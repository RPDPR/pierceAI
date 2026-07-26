import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://bot_user:bot_password_123@db:5432/pierceai_db")

# Default Bot Constants
TRIGGER_WORD = "g.p"
DEFAULT_COOLDOWN = 3.0

# Directory to save user-contributed pool images
IMAGE_POOL_DIR = "src/assets/pool/"
