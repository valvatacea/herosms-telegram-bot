import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
HEROSMS_API_KEY = os.getenv("HEROSMS_API_KEY")
HEROSMS_BASE_URL = os.getenv("HEROSMS_BASE_URL", "https://hero-sms.com/api/v1")

if not BOT_TOKEN or not HEROSMS_API_KEY:
    raise RuntimeError("Set BOT_TOKEN dan HEROSMS_API_KEY di .env")
