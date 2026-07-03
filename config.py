import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
SASTA_API_KEY = os.getenv("SASTA_API_KEY", "")
ADMIN_IDS = [
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
]
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "otp_bot")

# UPI Payment settings
UPI_ID = os.getenv("UPI_ID", "yourname@upi")
UPI_NAME = os.getenv("UPI_NAME", "OTP Bot")
UPI_MAIL = os.getenv("UPI_MAIL", "yourmail@gmail.com")
UPI_APP_PASS = os.getenv("UPI_APP_PASS", "")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "support")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0") or "0")
BOT_USERNAME = os.getenv("BOT_USERNAME", "")

GENQR_BASE = "https://subdict.qzz.io/genqr"
VERIFY_BASE = "https://subdict.qzz.io/check"

SASTA_BASE_URL = "https://sastaotp.com/api"
OTP_POLL_INTERVAL = 7
OTP_MAX_WAIT = 120

MIN_TOPUP = 10.0
MAX_TOPUP = 10000.0
