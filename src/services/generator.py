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
    def _sync_render_meme(
        user_avatar_bytes: bytes,
        pool_images: list,
        guild_pool_dir: str,
        top_raw: str,
        bottom_raw: str
    ) -> BytesIO:

        if pool_images and random.random() < 0.8:
            bg_path = os.path.join(guild_pool_dir, random.choice(pool_images))
            base_img = Image.open(bg_path).convert("RGB")
        else:
            base_img = Image.open(BytesIO(user_avatar_bytes)).convert("RGB")

        w, h = base_img.size
        draw = ImageDraw.Draw(base_img)

        margin = int(h * 0.0)
        max_text_width = int(w * 0.96)

        font_size = int(min(w, h) * 0.10)
        min_font_size = 18

        while font_size >= min_font_size:

            if os.path.exists(config.FONT_PATH):
                font = ImageFont.truetype(config.FONT_PATH, font_size)
            else:
                font = ImageFont.load_default()

            stroke_w = max(1, font_size // 20)
            spacing = max(1, font_size // 14)

            top_text = PierceGeneratorService._wrap_text_to_max_lines(
                top_raw.upper(),
                font,
                max_width=max_text_width,
                max_lines=2,
            )

            bottom_text = PierceGeneratorService._wrap_text_to_max_lines(
                bottom_raw.upper(),
                font,
                max_width=max_text_width,
                max_lines=2,
            )

            top_bbox = draw.multiline_textbbox(
                (0, 0),
                top_text,
                font=font,
                spacing=spacing,
                stroke_width=stroke_w,
                align="center"
            )

            bottom_bbox = draw.multiline_textbbox(
                (0, 0),
                bottom_text,
                font=font,
                spacing=spacing,
                stroke_width=stroke_w,
                align="center"
            )

            top_w = top_bbox[2] - top_bbox[0]
            top_h = top_bbox[3] - top_bbox[1]

            bottom_w = bottom_bbox[2] - bottom_bbox[0]
            bottom_h = bottom_bbox[3] - bottom_bbox[1]

            fits_width = (
                top_w <= max_text_width and
                bottom_w <= max_text_width
            )

            top_bottom = margin + top_h
            bottom_top = h - margin - bottom_h

            if fits_width and top_bottom + margin < bottom_top:
                break

            font_size -= 2

        draw.multiline_text(
            (w // 2, margin),
            top_text,
            font=font,
            fill="white",
            anchor="ma",
            align="center",
            spacing=spacing,
            stroke_width=stroke_w,
            stroke_fill="black",
        )

        draw.multiline_text(
            (w // 2, h - margin),
            bottom_text,
            font=font,
            fill="white",
            anchor="md",
            align="center",
            spacing=spacing,
            stroke_width=stroke_w,
            stroke_fill="black",
        )

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
            PierceGeneratorService._sync_render_meme, user_avatar_bytes, pool_images, guild_pool_dir, top_raw, bottom_raw
        )

    @staticmethod
    async def _fetch_clean_messages(guild_id: int) -> list[str]:
        async with AsyncSessionLocal() as session:
            blocked_stmt = select(ChannelConfig.channel_id).where(
                ChannelConfig.guild_id == guild_id, ChannelConfig.allow_read == False
            )
            blocked_result = await session.execute(blocked_stmt)
            blocked_ids = [row[0] for row in blocked_result.all() if row]

            stmt = select(Message.content).where(
                Message.guild_id == guild_id, not_(Message.channel_id.in_(blocked_ids))
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
        text_corpus = "\n".join(target_messages)

        try:
            def _build_and_make():
                text_model = markovify.NewlineText(text_corpus, state_size=1)
                text_model.compile(inplace=True)
                return text_model.make_short_sentence(max_chars=100, tries=100, test_output=False)

            if is_meme:
                discord_pattern = re.compile(r'<[!@#&:\w\s.-]+[^>]*>')
                attempts = 0
                max_attempts = 50

                while attempts < max_attempts:
                    attempts += 1

                    if random.random() < 0.10:
                        generated_text = random.choice(target_messages)
                    else:
                        generated_text = await asyncio.to_thread(_build_and_make)

                    if not generated_text:
                        continue

                    generated_text = generated_text.replace("\n", " ").replace("\r", " ").strip()

                    has_links = any(x in generated_text for x in ["http", "www.", "attachments/", "cdn.", ".com", ".ru", ".pl", ".net", ".org"])
                    has_pings_or_emojis = bool(discord_pattern.search(generated_text))

                    # has_bad_chars = bool(re.search(r'[\x00-\x1f\x7f-\x9f\xad]', generated_text))
                    # if has_bad_chars:
                    #     continue

                    if not has_links and not has_pings_or_emojis:
                        return generated_text

                fallback = random.choice(target_messages)
                fallback = discord_pattern.sub('', fallback)
                fallback = re.sub(r'https?://\S+|www\.\S+', '', fallback)
                return fallback.strip() if fallback.strip() else "ABSURD"

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
    def _wrap_text_to_max_lines(
        text: str,
        font: ImageFont.FreeTypeFont,
        max_width: int,
        max_lines: int = 2,
    ) -> str:

        words = text.split()

        if not words:
            return ""

        lines = []
        current = []

        for word in words:

            test = current + [word]
            line = " ".join(test)

            width = font.getbbox(line)[2]

            if width <= max_width:
                current.append(word)
            else:
                if current:
                    lines.append(" ".join(current))
                current = [word]

                if len(lines) >= max_lines:
                    break

        if current and len(lines) < max_lines:
            lines.append(" ".join(current))
        
        if len(lines) > max_lines:
            lines = lines[:max_lines]

        if len(lines) == max_lines and len(words) > 0:
            consumed = sum(len(l.split()) for l in lines)
            if consumed < len(words):
                remain = words[consumed:]
                lines[-1] += " " + " ".join(remain)

        return "\n".join(lines)