# pierceAI

pierceAI discord bot generates absurdity and nothing except absurdity!

---

## Quick Start

### 1. Environment Setup
Copy the example environment file and fill in your actual bot token:
```bash
cp .env.example .env
```

Now open `.env` and set uo your environment:
```env
DISCORD_TOKEN=your_discord_bot_token_here

DB_USER=pierceai_bot
DB_PASSWORD=
DB_PORT=5432
DB_NAME=pierceai_bot_db

DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@db:${DB_PORT}/${DB_NAME}
```

### 2. Run with Docker
Launch the entire infrastructure with a single command:
```bash
docker compose up --build -d
```

### 3. Initial Discord Server Setup
Once the bot joins your server, execute these slash commands as an Administrator:

1. **Enable bot access and configure permissions for a channel:**
   ```text
   /config channel_settings channel:#channel-name allow_read:True allow_write:True allow_save_images:True cooldown:3.0
   ```
2. **Sync historical data to populate the generation corpus:**
   ```text
   /config sync_history since_date:2026-01-01
   ```

### 4. Trigger
Type the trigger word in any authorized channel to generate a meme (`g.p` by default):
```text
g.p
```

---

## Maintenance & Logs

* **Restart the bot application:** `docker compose restart app`
* **View real-time logs:** `docker compose logs -f app`
* **Hard reset (wipe all data and volumes):** `docker compose down -v`

---

## Tech Stack

* **Language:** Python 3.11+ (Asyncio)
* **Framework:** discord.py (with application slash commands)
* **Database:** PostgreSQL 15
* **ORM:** SQLAlchemy 2.0 (Async mode)
* **Text Engine:** markovify (Markov chains algorithm)
* **Image Processing:** Pillow (PIL)
* **Asynchronous I/O:** aiohttp & aiofiles
* **Deployment:** Docker & Docker Compose