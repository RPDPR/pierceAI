import os
import random
import asyncio
import re
from io import BytesIO
import markovify
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import select, not_
from database import AsyncSessionLocal, Message, ChannelConfig
import config

class PierceGeneratorService:
    @staticmethod
    def _sync_render_meme(user_avatar_bytes: bytes, pool_images: list, guild_pool_dir: str, top_raw: str, bottom_raw: str) -> BytesIO:
        if pool_images and random.random() < 0.4:
            bg_path = os.path.join(guild_pool_dir, random.choice(pool_images))
            base_img = Image.open(bg_path).convert("RGB")
        else:
            base_img = Image.open(BytesIO(user_avatar_bytes)).convert("RGB")

        w, h = base_img.size
        draw = ImageDraw.Draw(base_img)
        font_size = max(16, int(w * 0.11))
        stroke_w = max(1, int(w * 0.007))
        max_text_w = int(w * 0.95)

        if os.path.exists(config.FONT_PATH):
            font = ImageFont.truetype(config.FONT_PATH, size=font_size)
        else:
            font = ImageFont.load_default()

        top_text = PierceGeneratorService._wrap_text_to_max_lines(top_raw.upper(), font, max_width=max_text_w, max_lines=2)
        bottom_text = PierceGeneratorService._wrap_text_to_max_lines(bottom_raw.upper(), font, max_width=max_text_w, max_lines=2)

        if top_text:
            if "\n" in top_text:
                bbox = draw.multiline_textbbox((0, 0), top_text, font=font, spacing=2, stroke_width=stroke_w)
                text_w = bbox[2] - bbox[0]
                x_pos = int((w - text_w) / 2)
                draw.multiline_text((x_pos, int(h * 0.00)), top_text, fill="white", font=font, align="center", spacing=2, stroke_width=stroke_w, stroke_fill="black")
            else:
                draw.multiline_text((int(w * 0.5), int(h * 0.00)), top_text, fill="white", font=font, anchor="ma", align="center", spacing=2, stroke_width=stroke_w, stroke_fill="black")

        if bottom_text:
            if "\n" in bottom_text:
                bbox = draw.multiline_textbbox((0, 0), bottom_text, font=font, spacing=2, stroke_width=stroke_w)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
                x_pos = int((w - text_w) / 2)
                y_pos = int(h * 0.98) - text_h
                draw.multiline_text((x_pos, y_pos), bottom_text, fill="white", font=font, align="center", spacing=2, stroke_width=stroke_w, stroke_fill="black")
            else:
                draw.multiline_text((int(w * 0.5), int(h * 0.98)), bottom_text, fill="white", font=font, anchor="mb", align="center", spacing=2, stroke_width=stroke_w, stroke_fill="black")

        output = BytesIO()
        base_img.save(output, format="JPEG", quality=95)
        output.seek(0)
        return output

    @staticmethod
    async def generate_meme(user_avatar_bytes: bytes, channel_id: int, guild_id: int) -> BytesIO:
        guild_pool_dir = os.path.join(config.IMAGE_POOL_DIR, str(guild_id))
        
        pool_images = []
        if await asyncio.to_thread(os.path.exists, guild_pool_dir):
            files = await asyncio.to_thread(os.listdir, guild_pool_dir)
            pool_images = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

        messages = await PierceGeneratorService._fetch_clean_messages(guild_id)
        
        top_raw = await PierceGeneratorService._generate_raw_text(messages, is_meme=True)
        bottom_raw = await PierceGeneratorService._generate_raw_text(messages, is_meme=True)

        return await asyncio.to_thread(
            PierceGeneratorService._sync_render_meme,
            user_avatar_bytes, pool_images, guild_pool_dir, top_raw, bottom_raw
        )

    @staticmethod
    async def _fetch_clean_messages(guild_id: int) -> list[str]:
        async with AsyncSessionLocal() as session:
            blocked_stmt = select(ChannelConfig.channel_id).where(
                ChannelConfig.guild_id == guild_id,
                ChannelConfig.allow_read == False
            )
            blocked_result = await session.execute(blocked_stmt)
            blocked_ids = [row[0] for row in blocked_result.all() if row]
            
            stmt = select(Message.content).where(
                Message.guild_id == guild_id,
                not_(Message.channel_id.in_(blocked_ids))
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    @staticmethod
    async def _generate_raw_text(messages: list[str], is_meme: bool = False) -> str:
        if len(messages) < 3:
            return "NOT ENOUGH DATA TO GENERATE ABSURDITY YET"
        if not is_meme and random.random() < 0.10:
            return random.choice(messages)

        target_messages = messages
        if is_meme:
            cleaned_messages = []
            for msg in messages:
                cleaned = msg.strip()
                if not cleaned or any(x in cleaned for x in ["http", "www.", "attachments/", "cdn."]):
                    continue
                if any(x in cleaned for x in [".com", ".ru", ".pl", ".net", ".org"]):
                    continue
                if re.search(r'<@&?\d+>', cleaned) or re.search(r'<#\d+>', cleaned) or re.search(r'<:\w+:\d+>', cleaned):
                    continue
                cleaned_messages.append(cleaned)
            target_messages = cleaned_messages

        if len(target_messages) < 3:
            return random.choice(messages)

        text_corpus = "\n".join(target_messages)
        try:
            def _build_and_make():
                text_model = markovify.NewlineText(text_corpus, state_size=1)
                text_model.compile(inplace=True)
                return text_model.make_short_sentence(max_chars=100, tries=100, test_output=False)

            if is_meme:
                for _ in range(10):
                    if random.random() < 0.10:
                        generated_text = random.choice(target_messages)
                    else:
                        generated_text = await asyncio.to_thread(_build_and_make)

                    if not generated_text:
                        generated_text = random.choice(target_messages)

                    has_links = any(x in generated_text for x in ["http", "www.", "attachments/", "cdn.", ".com", ".ru", ".pl", ".net", ".org"])
                    has_pings_or_emojis = bool(re.search(r'<@&?\d+>|<#\d+>|<:\w+:\d+>', generated_text))

                    if not has_links and not has_pings_or_emojis:
                        return generated_text
                
                return "ABSURD"
            else:
                generated_text = await asyncio.to_thread(_build_and_make)
                return generated_text if generated_text else random.choice(target_messages)
        except Exception:
            return random.choice(target_messages)

    @staticmethod
    async def get_text_for_reply(guild_id: int) -> str:
        messages = await PierceGeneratorService._fetch_clean_messages(guild_id)
        return await PierceGeneratorService._generate_raw_text(messages, is_meme=False)

    @staticmethod
    def _wrap_text_to_max_lines(text: str, font: ImageFont.FreeTypeFont, max_width: int, max_lines: int = 2) -> str:
        words = text.split()
        lines = []
        current_line = []
        for word in words:
            current_line.append(word)
            test_line = " ".join(current_line)
            bbox = font.getbbox(test_line)
            width = bbox[2] - bbox[0]
            if width > max_width:
                if len(current_line) > 1:
                    current_line.pop()
                    lines.append(" ".join(current_line))
                    current_line = [word]
                else:
                    lines.append(test_line)
                    current_line = []
            if len(lines) >= max_lines:
                break
        if len(lines) < max_lines and current_line:
            lines.append(" ".join(current_line))
        return "\n".join(lines[:max_lines])