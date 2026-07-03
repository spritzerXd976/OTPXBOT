# SastaOTP Telegram Reseller Bot

A Telegram bot that resells SMS OTP virtual numbers from the [SastaOTP](https://sastaotp.com) API with a configurable markup. Users browse services/countries, pay from an internal wallet, receive a virtual number, and get the OTP delivered automatically.

## Features

- **User flow**: `/start` menu → pick service → pick country → confirm price → pay from wallet → receive number → OTP auto-delivered
- **Wallet system**: per-user balance, UPI QR top-up with UTR/TXN verification, redeem codes, automatic refund on timeout/cancel
- **UPI QR payments**: generates a QR via `subdict.qzz.io/genqr`, user pays, then verifies via UTR or TXN ID using `subdict.qzz.io/check`
- **Redeem codes**: admins generate codes (`/genredeem`), users redeem via the menu button
- **OTP polling**: polls SastaOTP every 7s for up to 120s; refunds automatically if no OTP arrives
- **Markup pricing**: `user_price = base_price × (1 + markup% / 100)`, configurable via admin
- **Profile & referrals**: users see stats and a referral link (`/start <user_id>`)
- **Admin panel** (Telegram): manage balances, set markup, list users/orders, broadcast, profit report, generate redeem codes
- **MongoDB** storage (users, orders, settings, topups, redeem_codes) via `motor`

## Tech Stack

- Python 3.10+
- `python-telegram-bot` v21 (async)
- `motor` (async MongoDB driver)
- `httpx` (async HTTP for SastaOTP API)
- `python-dotenv`

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

Copy `.env.example` to `.env` and fill in:

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | From [@BotFather](https://t.me/BotFather) |
| `SASTA_API_KEY` | Your SastaOTP API key |
| `ADMIN_IDS` | Comma-separated Telegram user IDs of admins |
| `MONGO_URI` | MongoDB connection string |
| `MONGO_DB` | Database name (default: `otp_bot`) |
| `UPI_ID` | UPI ID for receiving payments (e.g. `iybhathstalker@fam`) |
| `UPI_NAME` | Display name for UPI (e.g. `DRX Net`) |
| `UPI_MAIL` | Gmail address used for payment verification API |
| `UPI_APP_PASS` | Gmail app password for the verification API |
| `SUPPORT_USERNAME` | Telegram username for support contact |

### 3. Get your Telegram user ID

Message [@userinfobot](https://t.me/userinfobot) to get your numeric Telegram ID, then add it to `ADMIN_IDS`.

### 4. Run

```bash
python bot.py
```

## Commands

### User

| Command | Action |
|---|---|
| `/start` | Welcome + main menu |
| `/balance` | Show wallet balance |
| `/buy` | Browse services & buy a number |
| `/history` | Recent orders |
| `/topup` | Add funds via UPI QR |
| `/profile` | Profile + referral link |
| `/redeem` | Redeem a code |
| `/cancel` | Cancel an active order (auto-refund) |
| `/support` | Contact support |

### Admin

| Command | Action |
|---|---|
| `/admin` | Admin dashboard |
| `/addbalance <user_id> <amount>` | Credit a user |
| `/removebalance <user_id> <amount>` | Debit a user |
| `/setmarkup <percentage>` | Set global markup % |
| `/users` | List all users |
| `/orders` | Recent orders |
| `/broadcast <message>` | Message all users |
| `/profit` | Profit report (charged − SastaOTP cost) |
| `/genredeem <amount>` | Generate a redeem code |

## How the markup works

1. Bot fetches the base price from SastaOTP for the selected service/country.
2. Applies: `user_price = base_price × (1 + markup% / 100)`.
3. User pays `user_price` from their wallet.
4. Bot stores both `base_cost` and `charged_amount` per order for profit tracking.

## UPI QR payment flow

1. User taps *Add Funds* → selects amount (or custom).
2. Bot generates a QR code via `https://subdict.qzz.io/genqr?upi=...&amount=...&name=...`.
3. User scans and pays via any UPI app.
4. User taps *I've Paid* and enters their UTR or TXN ID.
5. Bot verifies via `https://subdict.qzz.io/check?mail=...&apppass=...&utr=...&amount=...` (falls back to `txnid=` if UTR not found).
6. On success, wallet is credited automatically.

## OTP flow

1. After purchase, the bot polls `getStatus` every 7 seconds.
2. On `STATUS_OK:<code>`, the OTP is sent to the user and the order marked completed.
3. If no OTP arrives within 120s, the bot cancels the activation on SastaOTP (`status=8`) and refunds the user.

## Project structure

```
.
├── bot.py          # Main bot: handlers, keyboards, OTP polling, admin
├── sastaotp.py     # SastaOTP API client (httpx async)
├── database.py     # MongoDB access layer (motor)
├── config.py       # Env config
├── requirements.txt
├── .env.example
└── README.md
```

## Notes

- The SastaOTP API response shapes can vary; the client handles both JSON and plain-text (`ACCESS_NUMBER:ID:PHONE`) formats.
- Admin commands are gated by the `ADMIN_IDS` allowlist — non-admins get no response.
- All money values are in INR (₹), matching SastaOTP's pricing.
