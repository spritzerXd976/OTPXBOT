import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8401941077:AAHXk-k6lc5LJBcsnfsulnnSRBHwy2n_DoQ")
SASTA_API_KEY = os.getenv("SASTA_API_KEY", "stp_8a340671ee258ff31b6d3586e2d7c45f64197d37f8a3d2d4")
ADMIN_IDS = [
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "6035523795").split(",")
    if x.strip().isdigit()
]
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://Mafia:Mafia@mafia.wvuzxgl.mongodb.net/?retryWrites=true&w=majority")
MONGO_DB = os.getenv("MONGO_DB", "otp_bot")

# UPI Payment settings
UPI_ID = os.getenv("UPI_ID", "niteshjsr@fam")
UPI_NAME = os.getenv("UPI_NAME", "OTP Bot")
UPI_MAIL = os.getenv("UPI_MAIL", "protricks72@gmail.com")
UPI_APP_PASS = os.getenv("UPI_APP_PASS", "blbn pcre pkre bgln")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "NullXShadow")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "-1002234925242") or "0")
BOT_USERNAME = os.getenv("BOT_USERNAME", "YumiiXbot")

GENQR_BASE = "https://subdict.qzz.io/genqr"
VERIFY_BASE = "https://subdict.qzz.io/check"

SASTA_BASE_URL = "https://sastaotp.com/api"
OTP_POLL_INTERVAL = 7
OTP_MAX_WAIT = 120

MIN_TOPUP = 10.0
MAX_TOPUP = 10000.0
