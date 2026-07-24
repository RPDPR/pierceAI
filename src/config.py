import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://bot_user:bot_password_123@db:5432/pierceai_db")

# Default Bot Constants
TRIGGER_WORD = "g.i"
DEFAULT_COOLDOWN = 0.0          # No cooldown by default for your private server
DEFAULT_HISTORY_DAYS = 30       # Take messages from last 30 days by default
DEFAULT_TEXT_POSITION = "random" # "top", "bottom", "random"

# Directory to save user-contributed pool images
IMAGE_POOL_DIR = "src/assets/pool/"
