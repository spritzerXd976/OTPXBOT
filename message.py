"""All user-facing message templates for the OTP reseller bot."""

from config import (
    UPI_ID,
    UPI_NAME,
    SUPPORT_USERNAME,
    OTP_MAX_WAIT,
    MIN_TOPUP,
    MAX_TOPUP,
    BOT_USERNAME,
)


def fmt_money(n: float) -> str:
    return f"₹{n:.2f}"


# ---- welcome / menu ----

WELCOME = (
    "👋 *Welcome, {name}!*\n\n"
    "📱 *SMS OTP Reseller Bot*\n"
    "Buy virtual numbers for WhatsApp, Telegram, Instagram and 200+ services.\n\n"
    "💰 Your Balance: *{balance}*\n\n"
    "Tap a button below to get started 👇"
)

BALANCE = "💰 *Your Balance:* {balance}{pending}"

NO_ORDERS = "📜 You have no orders yet."

HISTORY_HEADER = "📜 *Recent Orders*\n"

HISTORY_ROW = "{emoji} `{order_id}` | {service}\n   {phone} | {amount}"

# ---- buy flow ----

SELECT_SERVICE = "🛒 *Select a service:*"

SERVICES_LOAD_FAIL = "⚠️ Could not load services. Try again later."

SERVICES_REFRESHED = "🔄 Services refreshed. Use /buy again."

COUNTRIES_LOAD_FAIL = "⚠️ Could not load countries."

SELECT_COUNTRY = "🌍 *Select country:*"

NO_COUNTRY_LIST = "No country list returned. Using auto."

CONFIRM_PURCHASE = (
    "🛒 *Order Summary*\n\n"
    "🌍 Country: `{country}`\n"
    "📱 Service: `{service}`\n"
    "💵 Price: *{charged}*\n"
    "💰 Your Balance: {balance}\n\n"
    "Confirm to purchase this number?"
)

INSUFFICIENT_BALANCE = (
    "❌ *Insufficient Balance*\n\n"
    "💰 Required: *{required}*\n"
    "💳 Your Balance: *{balance}*\n"
    "📉 Shortage: *{shortage}*\n\n"
    "Please recharge your wallet to continue."
)

SESSION_EXPIRED_BUY = "⚠️ Session expired. Use /buy again."

API_ERROR = "⚠️ API error: {error}"

NUMBER_FAIL = "⚠️ Could not get a number. Response: `{response}`"

NUMBER_PURCHASED = (
    "✅ *Number Purchased!*\n\n"
    "🆔 Order ID: `{order_id}`\n"
    "📱 Number: `{phone}`\n"
    "📲 Service: {service}\n"
    "🌍 Country: {country}\n"
    "💵 Amount: {amount}\n\n"
    "⏳ Waiting for OTP... (up to {max_wait}s)\n\n"
    "You'll receive the OTP here automatically."
)

PURCHASE_CANCELLED = "❌ Purchase cancelled."

# ---- OTP ----

OTP_RECEIVED = (
    "📩 *OTP Received!*\n\n"
    "🆔 Order: `{order_id}`\n"
    "📱 Service: {service}\n"
    "🔑 OTP: `{code}`\n\n"
    "Do not share this code with anyone."
)

OTP_TIMEOUT = (
    "⌛ *OTP Timeout*\n\n"
    "No OTP received within the time limit.\n\n"
    "🛒 Order: `{order_id}`\n"
    "↩️ Status: Cancelled\n"
    "💰 Refunded: {amount} to your wallet"
)

# ---- cancel ----

NO_ACTIVE_ORDERS = "You have no active orders to cancel."

SELECT_CANCEL = "Select order to cancel:"

ORDER_NOT_ACTIVE = "Order not found or not active."

ORDER_CANCELLED = "✅ Order `{order_id}` cancelled.\n↩️ {amount} refunded."

# ---- topup ----

TOPUP_START = (
    "➕ *Add Funds to Wallet*\n\n"
    "Select an amount or enter a custom amount.\n\n"
    "💳 UPI ID: `{upi_id}`\n"
    "👤 Name: {upi_name}\n\n"
    "After payment, you'll enter your UTR/TXN ID to verify."
)

CUSTOM_AMOUNT_PROMPT = "✏️ Send the amount you want to add (e.g. `150`):"

AMOUNT_OUT_OF_RANGE = (
    "❌ Amount must be between "
    f"{fmt_money(MIN_TOPUP)} and {fmt_money(MAX_TOPUP)}."
)

PAYMENT_INSTRUCTIONS = (
    "💳 *Payment of {amount}*\n\n"
    "Scan the QR code below to pay via any UPI app.\n\n"
    "💳 UPI ID: `{upi_id}`\n"
    "👤 Name: {upi_name}\n"
    "💰 Amount: *{amount}*\n\n"
    "After payment, tap *Deposit Done* and enter your UTR/TXN ID."
)

QR_CAPTION_INLINE = "Scan to pay {amount}"

TOPUP_PAID_PROMPT = (
    "📝 *Enter UTR / TXN ID*\n\n"
    "Please send your UTR or Transaction ID from your UPI app's payment receipt.\n\n"
    "Example: `412345678901`"
)

TOPUP_SESSION_EXPIRED = "⚠️ Session expired. Use /topup again."

TOPUP_CANCELLED = "❌ Top-up cancelled."

INVALID_UTR = "❌ Invalid UTR/TXN ID. Try /topup again."

VERIFYING = "⏳ Verifying payment..."

PAYMENT_VERIFIED = (
    "✅ *Payment Verified!*\n\n"
    "💰 Amount: {amount}\n"
    "💳 Added to wallet\n"
    "🆔 UTR/TXN: `{ref}`\n"
    "💰 New Balance: *{balance}*\n\n"
    "You can now purchase numbers!"
)

PAYMENT_NOT_FOUND = (
    "❌ *Payment Not Found*\n\n"
    "Could not verify your payment. Please check:\n"
    "• UTR/TXN ID is correct\n"
    "• Amount matches exactly ({amount})\n"
    "• Payment was successful\n\n"
    f"If you've already paid, contact @{SUPPORT_USERNAME}."
)

VERIFY_ERROR = "⚠️ Verification error: {error}"

INVALID_AMOUNT = "❌ Invalid amount. Use /topup to try again."

# ---- redeem ----

REDEEM_PROMPT = "🎁 Send the redeem code to add funds to your wallet:"

REDEEM_CANCELLED = "❌ Redeem cancelled."

REDEEM_INVALID = "❌ Invalid redeem code."

REDEEM_USED = "❌ This code has already been used."

REDEEM_SUCCESS = (
    "✅ Redeemed! {amount} added to your wallet.\n"
    "New balance: {balance}"
)

# ---- profile ----

PROFILE = (
    "👤 *Your Profile*\n\n"
    "User ID: `{user_id}`\n"
    "Username: @{username}\n"
    "Balance: {balance}\n"
    "Total orders: {total}\n"
    "Completed: {completed}\n"
    "Total spent: {spent}\n"
    "{ref_line}\n\n"
    "🔗 Your referral link:\n"
    "`https://t.me/{bot_username}?start={user_id}`"
)

# ---- support ----

SUPPORT = f"📞 *Support*\n\nContact us: @{SUPPORT_USERNAME}"

# ---- misc ----

USE_MENU = "Use the menu or /start."

ADMINS_ONLY = "⛔ Admins only."

# ---- channel logs ----

CHANNEL_PURCHASE_LOG = (
    "✅ *New Number Purchase Successful*\n\n"
    "🌍 Country: `{country}`\n"
    "📱 Application: `{service}`\n"
    "🔢 Number: `{phone_masked}`\n"
    "🔑 OTP: `{otp_masked}`\n"
    "🛒 Order ID: `{order_id}`\n"
    "👤 User: `{username}` (`{user_id}`)\n"
    "💵 Amount: {amount}\n"
    "🕐 Time: {time}\n\n"
    "━━━━━━━━━━━━━━━\n"
    f"🤖 Bot: @{BOT_USERNAME}\n"
    f"📞 Support: @{SUPPORT_USERNAME}"
)

CHANNEL_OTP_LOG = (
    "📩 *OTP Received*\n\n"
    "🛒 Order: `{order_id}`\n"
    "📱 Service: `{service}`\n"
    "🔑 OTP: `{otp}`\n"
    "👤 User: `{username}` (`{user_id}`)\n\n"
    "━━━━━━━━━━━━━━━\n"
    f"🤖 Bot: @{BOT_USERNAME}"
)

CHANNEL_TOPUP_LOG = (
    "💰 *Wallet Recharge Successful*\n\n"
    "👤 User: `{username}` (`{user_id}`)\n"
    "💵 Amount: {amount}\n"
    "🆔 UTR/TXN: `{ref}`\n"
    "💳 New Balance: {balance}\n"
    "🕐 Time: {time}\n\n"
    "━━━━━━━━━━━━━━━\n"
    f"🤖 Bot: @{BOT_USERNAME}\n"
    f"📞 Support: @{SUPPORT_USERNAME}"
)

# ---- admin ----

ADMIN_PANEL = (
    "🛠 *Admin Panel*\n\n"
    "👥 Users: {users}\n"
    "⏳ Pending orders: {pending}\n"
    "✅ Completed orders: {completed}\n"
    "📈 Current markup: {markup}%\n\n"
    "*Commands:*\n"
    "/addbalance <user_id> <amount>\n"
    "/removebalance <user_id> <amount>\n"
    "/setmarkup <percentage>\n"
    "/users — list users\n"
    "/orders — recent orders\n"
    "/broadcast <message>\n"
    "/profit — profit report\n"
    "/genredeem <amount> — generate redeem code"
)

ADDBALANCE_USAGE = "Usage: /addbalance <user_id> <amount>"

ADDBALANCE_DONE = "✅ Added {amount} to {user_id}."

REMOVEBALANCE_USAGE = "Usage: /removebalance <user_id> <amount>"

REMOVEBALANCE_DONE = "✅ Removed {amount} from {user_id}."

SETMARKUP_USAGE = "Usage: /setmarkup <percentage>"

SETMARKUP_DONE = "✅ Markup set to {markup}%."

INVALID_ARGS = "Invalid arguments."

INVALID_PERCENT = "Invalid percentage."

USERS_HEADER = "👥 *Users ({count})*\n"

USERS_ROW = "• {user_id} | @{username} | {balance}"

NO_ORDERS_ADMIN = "No orders."

ORDERS_HEADER = "📋 *Recent Orders*\n"

ORDERS_ROW = "• `{order_id}` | u{user_id} | {service} | {status} | {amount}"

BROADCAST_USAGE = "Usage: /broadcast <message>"

BROADCAST_DONE = "✅ Broadcast sent to {sent}/{total} users."

BROADCAST_MSG = "📢 {message}"

PROFIT_REPORT = (
    "📊 *Profit Report*\n\n"
    "Orders: {count}\n"
    "Total cost (SastaOTP): {base}\n"
    "Total charged: {charged}\n"
    "*Profit: {profit}*"
)

GENREDEEM_USAGE = "Usage: /genredeem <amount>"

GENREDEEM_INVALID = "Invalid amount."

GENREDEEM_DONE = "✅ Redeem code generated:\n\n`{code}`\nValue: {amount}"

# ---- status emoji map ----

STATUS_EMOJI = {
    "pending": "⏳",
    "completed": "✅",
    "cancelled": "❌",
    "refunded": "↩️",
}
