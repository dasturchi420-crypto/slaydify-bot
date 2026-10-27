import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

FREE_CREDITS = int(os.getenv("FREE_CREDITS", "3"))
MAX_PARALLEL = int(os.getenv("MAX_PARALLEL", "3"))
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()}

DB_PATH = os.getenv("DB_PATH", "bot.db")
OUT_DIR = os.getenv("OUT_DIR", "out")
