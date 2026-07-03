import asyncio
import datetime
import logging
import uuid

import httpx
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

import database as db
import sastaotp
import message as msg
from config import (
    TELEGRAM_BOT_TOKEN,
    ADMIN_IDS,
    OTP_POLL_INTERVAL,
    OTP_MAX_WAIT,
    UPI_ID,
    UPI_NAME,
    UPI_MAIL,
    UPI_APP_PASS,
    GENQR_BASE,
    VERIFY_BASE,
    MIN_TOPUP,
    MAX_TOPUP,
    LOG_CHANNEL_ID,
    BOT_USERNAME,
)

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("otpbot")

# ---------- helpers ----------


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def apply_markup(base: float, markup_pct: float) -> float:
    return round(base * (1 + markup_pct / 100.0), 2)


def mask(s: str, visible: int = 2) -> str:
    if not s:
        return "—"
    if len(s) <= visible:
        return s
    return s[:visible] + "*" * (len(s) - visible)


async def log_to_channel(ctx: ContextTypes.DEFAULT_TYPE, text: str):
    if not LOG_CHANNEL_ID:
        return
    try:
        await ctx.bot.send_message(
            LOG_CHANNEL_ID, text, parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
    except Exception as e:
        log.warning("log_to_channel failed: %s", e)


async def ensure_user(update: Update, ref_by=None):
    tg = update.effective_user
    admin = is_admin(tg.id)
    user = await db.get_user(tg.id)
    if user is None:
        user = await db.create_user(tg.id, tg.username, admin, ref_by)
    else:
        if user.get("is_admin") != admin or user.get("username") != (tg.username or ""):
            await db.users_col.update_one(
                {"user_id": tg.id},
                {"$set": {"is_admin": admin, "username": tg.username or ""}},
            )
    return user


# ---------- shared inline keyboards ----------

def home_kb(is_adm: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("🛒 Buy Number", callback_data="menu:buy"),
         InlineKeyboardButton("💰 Balance", callback_data="menu:balance")],
        [InlineKeyboardButton("📜 History", callback_data="menu:history"),
         InlineKeyboardButton("➕ Add Funds", callback_data="menu:topup")],
        [InlineKeyboardButton("👤 Profile", callback_data="menu:profile"),
         InlineKeyboardButton("🎁 Redeem", callback_data="menu:redeem")],
        [InlineKeyboardButton("❌ Cancel Order", callback_data="menu:cancel"),
         InlineKeyboardButton("📞 Support", callback_data="menu:support")],
    ]
    if is_adm:
        rows.append([InlineKeyboardButton("🛠 Admin Panel", callback_data="menu:admin")])
    return InlineKeyboardMarkup(rows)


def back_home_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Home", callback_data="menu:home")]])


def back_cancel_kb(back_cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back", callback_data=back_cb),
         InlineKeyboardButton("❌ Cancel", callback_data="menu:home")],
    ])


# ---------- start / menu ----------


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ref_by = None
    if ctx.args:
        try:
            ref_by = int(ctx.args[0])
            if ref_by == update.effective_user.id:
                ref_by = None
        except ValueError:
            ref_by = None
    user = await ensure_user(update, ref_by)
    name = update.effective_user.first_name or "there"
    bal = user.get("balance", 0.0)
    text = msg.WELCOME.format(name=name, balance=msg.fmt_money(bal))
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=home_kb(user.get("is_admin")),
    )


async def cb_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    action = q.data.split(":", 1)[1]
    user = await ensure_user(update)

    if action == "home":
        await _show_home(q, user)
    elif action == "buy":
        await _show_buy(q, ctx)
    elif action == "balance":
        pend = await db.get_pending_topups(user["user_id"])
        pend_txt = f"\n⏳ Pending top-ups: {len(pend)}" if pend else ""
        await q.edit_message_text(
            msg.BALANCE.format(balance=msg.fmt_money(user.get("balance", 0.0)), pending=pend_txt),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_home_kb(),
        )
    elif action == "history":
        await _show_history(q, user)
    elif action == "topup":
        await _show_topup(q, ctx)
    elif action == "profile":
        await _show_profile(q, user, ctx)
    elif action == "redeem":
        ctx.user_data["awaiting_redeem"] = True
        await q.edit_message_text(
            msg.REDEEM_PROMPT,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="menu:home")]]),
        )
    elif action == "cancel":
        await _show_cancel(q, user)
    elif action == "support":
        await q.edit_message_text(
            msg.SUPPORT, parse_mode=ParseMode.MARKDOWN, reply_markup=back_home_kb()
        )
    elif action == "admin":
        await _show_admin(q, user)


async def _show_home(q, user):
    name = "there"
    bal = user.get("balance", 0.0)
    text = msg.WELCOME.format(name=name, balance=msg.fmt_money(bal))
    await q.edit_message_text(
        text, parse_mode=ParseMode.MARKDOWN, reply_markup=home_kb(user.get("is_admin"))
    )


async def _show_profile(q, user, ctx):
    orders = await db.get_user_orders(user["user_id"], 100)
    total = len(orders)
    completed = sum(1 for o in orders if o.get("status") == "completed")
    spent = sum(o.get("charged_amount", 0) for o in orders if o.get("status") == "completed")
    ref = user.get("ref_by")
    ref_line = f"Referred by: `{ref}`" if ref else "Referred by: —"
    text = msg.PROFILE.format(
        user_id=user["user_id"],
        username=user.get("username", "—"),
        balance=msg.fmt_money(user.get("balance", 0)),
        total=total,
        completed=completed,
        spent=msg.fmt_money(spent),
        ref_line=ref_line,
        bot_username=ctx.bot.username,
    )
    await q.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=back_home_kb())


async def _show_history(q, user):
    orders = await db.get_user_orders(user["user_id"], 10)
    if not orders:
        await q.edit_message_text(msg.NO_ORDERS, reply_markup=back_home_kb())
        return
    lines = [msg.HISTORY_HEADER]
    for o in orders:
        emoji = msg.STATUS_EMOJI.get(o["status"], "•")
        lines.append(
            msg.HISTORY_ROW.format(
                emoji=emoji,
                order_id=o["order_id"][:8],
                service=o["service"],
                phone=o.get("phone_number", "—"),
                amount=msg.fmt_money(o["charged_amount"]),
            )
        )
    await q.edit_message_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=back_home_kb())


async def _show_cancel(q, user):
    orders = await db.get_user_orders(user["user_id"], 10)
    pending = [o for o in orders if o.get("status") == "pending"]
    if not pending:
        await q.edit_message_text(msg.NO_ACTIVE_ORDERS, reply_markup=back_home_kb())
        return
    kb = [[InlineKeyboardButton(f"❌ {o['order_id'][:8]} — {o['service']}", callback_data=f"cancel:{o['order_id']}")]
          for o in pending]
    kb.append([InlineKeyboardButton("🏠 Home", callback_data="menu:home")])
    await q.edit_message_text(msg.SELECT_CANCEL, reply_markup=InlineKeyboardMarkup(kb))


async def _show_admin(q, user):
    if not user.get("is_admin"):
        await q.edit_message_text(msg.ADMINS_ONLY, reply_markup=back_home_kb())
        return
    users_n = await db.count_users()
    pend = await db.count_orders_by_status("pending")
    comp = await db.count_orders_by_status("completed")
    markup = await db.get_setting("markup_pct", 30.0)
    text = msg.ADMIN_PANEL.format(users=users_n, pending=pend, completed=comp, markup=markup)
    await q.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=back_home_kb())


# ---------- buy flow ----------

SERVICES_CACHE = {}


async def load_services():
    global SERVICES_CACHE
    if SERVICES_CACHE:
        return SERVICES_CACHE
    try:
        data = await sastaotp.get_services_list()
        SERVICES_CACHE = data
    except Exception as e:
        log.warning("get_services_list failed: %s", e)
    return SERVICES_CACHE


async def _show_buy(q, ctx):
    data = await load_services()
    services = data.get("services") or data.get("data") or []
    if not services:
        await q.edit_message_text(msg.SERVICES_LOAD_FAIL, reply_markup=back_home_kb())
        return
    kb = []
    for s in services[:30]:
        code = s.get("service") or s.get("code") or s.get("id")
        name = s.get("name") or code
        kb.append([InlineKeyboardButton(f"📱 {name}", callback_data=f"svc:{code}")])
    kb.append([InlineKeyboardButton("🔄 Refresh", callback_data="svc:refresh")])
    kb.append([InlineKeyboardButton("🏠 Home", callback_data="menu:home")])
    await q.edit_message_text(
        msg.SELECT_SERVICE, parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(kb),
    )


async def cb_service(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    if data == "svc:refresh":
        global SERVICES_CACHE
        SERVICES_CACHE = {}
        await load_services()
        await _show_buy(q, ctx)
        return
    code = data.split(":", 1)[1]
    ctx.user_data["buy_service"] = code
    try:
        svc_data = await sastaotp.get_services(code)
    except Exception:
        await q.edit_message_text(msg.COUNTRIES_LOAD_FAIL, reply_markup=back_home_kb())
        return
    countries = []
    if isinstance(svc_data, list):
        countries = svc_data
    elif isinstance(svc_data, dict):
        countries = svc_data.get("countries") or svc_data.get("data") or []
    kb = []
    for c in countries[:25]:
        cc = c.get("country_code") or c.get("code") or c.get("id")
        name = c.get("name") or c.get("country") or cc
        price = c.get("price") or c.get("cost") or "?"
        kb.append([InlineKeyboardButton(f"🌍 {name} — {price}", callback_data=f"ctry:{cc}:{price}")])
    kb.append([InlineKeyboardButton("🌐 Auto (any country)", callback_data="ctry:auto:0")])
    kb.append([InlineKeyboardButton("⬅️ Back", callback_data="menu:buy"),
               InlineKeyboardButton("🏠 Home", callback_data="menu:home")])
    if not countries:
        ctx.user_data["buy_country"] = ""
        ctx.user_data["buy_base"] = 0.0
        await q.edit_message_text(
            msg.NO_COUNTRY_LIST,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Continue", callback_data="buy_confirm")],
                [InlineKeyboardButton("🏠 Home", callback_data="menu:home")],
            ]),
        )
        return
    await q.edit_message_text(
        msg.SELECT_COUNTRY, parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(kb),
    )


async def cb_country(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    parts = q.data.split(":")
    ctry = parts[1]
    base_str = parts[2] if len(parts) > 2 else "0"
    try:
        base = float(base_str)
    except (ValueError, TypeError):
        base = 0.0
    ctx.user_data["buy_country"] = "" if ctry == "auto" else ctry
    ctx.user_data["buy_base"] = base
    markup = await db.get_setting("markup_pct", 30.0)
    charged = apply_markup(base, markup) if base else 0.0
    ctx.user_data["buy_charged"] = charged
    user = await db.get_user(update.effective_user.id)
    bal = user.get("balance", 0.0)
    text = msg.CONFIRM_PURCHASE.format(
        service=ctx.user_data.get("buy_service"),
        country=ctry,
        charged=msg.fmt_money(charged),
        balance=msg.fmt_money(bal),
    )
    kb = [
        [InlineKeyboardButton("✅ Confirm & Pay", callback_data="buy_confirm")],
        [InlineKeyboardButton("⬅️ Back", callback_data=f"svc:{ctx.user_data.get('buy_service', '')}"),
         InlineKeyboardButton("🏠 Home", callback_data="menu:home")],
    ]
    await q.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(kb))


async def cb_buy_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = await ensure_user(update)
    service = ctx.user_data.get("buy_service")
    country = ctx.user_data.get("buy_country", "")
    charged = ctx.user_data.get("buy_charged", 0.0)
    if not service:
        await q.edit_message_text(msg.SESSION_EXPIRED_BUY, reply_markup=back_home_kb())
        return
    if user.get("balance", 0.0) < charged:
        kb = [[InlineKeyboardButton("💰 Recharge Now", callback_data="menu:topup")],
              [InlineKeyboardButton("🏠 Home", callback_data="menu:home")]]
        await q.edit_message_text(
            msg.INSUFFICIENT_BALANCE.format(
                required=msg.fmt_money(charged),
                balance=msg.fmt_money(user.get("balance", 0.0)),
                shortage=msg.fmt_money(charged - user.get("balance", 0.0)),
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(kb),
        )
        return
    try:
        resp = await sastaotp.get_number(service, country)
    except Exception as e:
        await q.edit_message_text(msg.API_ERROR.format(error=e), reply_markup=back_home_kb())
        return
    sasta_id = None
    phone = None
    if isinstance(resp, dict):
        sasta_id = resp.get("activation_id") or resp.get("id")
        phone = resp.get("phone") or resp.get("phone_number")
        if not sasta_id:
            txt = resp.get("response") or resp.get("data") or ""
            if isinstance(txt, str) and "ACCESS_NUMBER" in txt:
                parts = txt.split(":")
                if len(parts) >= 3:
                    sasta_id, phone = parts[1], parts[2]
    if not sasta_id:
        await q.edit_message_text(
            msg.NUMBER_FAIL.format(response=str(resp)[:200]),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_home_kb(),
        )
        return
    await db.update_balance(user["user_id"], -charged)
    order_id = uuid.uuid4().hex[:12]
    order = {
        "order_id": order_id,
        "user_id": user["user_id"],
        "service": service,
        "country": country,
        "phone_number": phone or "",
        "sasta_id": sasta_id,
        "base_cost": ctx.user_data.get("buy_base", 0.0),
        "charged_amount": charged,
        "status": "pending",
        "otp_received": "",
        "created_at": datetime.datetime.utcnow(),
    }
    await db.create_order(order)
    await q.edit_message_text(
        msg.NUMBER_PURCHASED.format(
            order_id=order_id, phone=phone, service=service,
            country=country or "Auto", amount=msg.fmt_money(charged), max_wait=OTP_MAX_WAIT
        ),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_home_kb(),
    )
    await log_to_channel(ctx, msg.CHANNEL_PURCHASE_LOG.format(
        country=country or "Auto", service=service,
        phone_masked=mask(phone or ""), otp_masked="⏳ Pending",
        order_id=order_id, username=user.get("username", "—"),
        user_id=user["user_id"], amount=msg.fmt_money(charged),
        time=datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    ))
    ctx.application.create_task(poll_otp(ctx, user["user_id"], order_id, sasta_id))


async def cb_buy_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await _show_home(q, await ensure_user(update))


# ---------- OTP polling ----------


async def poll_otp(ctx: ContextTypes.DEFAULT_TYPE, user_id: int, order_id: str, sasta_id: str):
    deadline = asyncio.get_event_loop().time() + OTP_MAX_WAIT
    last_code = ""
    while asyncio.get_event_loop().time() < deadline:
        try:
            st = await sastaotp.get_status(sasta_id)
        except Exception as e:
            log.warning("poll status error: %s", e)
            await asyncio.sleep(OTP_POLL_INTERVAL)
            continue
        code = ""
        if isinstance(st, dict):
            code = st.get("code") or st.get("sms") or ""
            if not code:
                raw = st.get("response") or st.get("status") or ""
                if isinstance(raw, str) and raw.startswith("STATUS_OK"):
                    code = raw.split(":", 1)[1] if ":" in raw else ""
        elif isinstance(st, str) and st.startswith("STATUS_OK"):
            code = st.split(":", 1)[1] if ":" in st else ""
        if code and code != last_code:
            last_code = code
            await db.update_order(order_id, {"status": "completed", "otp_received": code})
            try:
                await sastaotp.set_status(sasta_id, 1)
            except Exception:
                pass
            order = await db.get_order(order_id)
            await ctx.bot.send_message(
                user_id,
                msg.OTP_RECEIVED.format(code=code, order_id=order_id, service=order.get("service", "—")),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=back_home_kb(),
            )
            await log_to_channel(ctx, msg.CHANNEL_OTP_LOG.format(
                order_id=order_id, service=order.get("service", "—"),
                otp=code, username=order.get("username", "—"), user_id=user_id,
            ))
            return
        await asyncio.sleep(OTP_POLL_INTERVAL)
    try:
        await sastaotp.set_status(sasta_id, 8)
    except Exception:
        pass
    order = await db.get_order(order_id)
    if order and order.get("status") == "pending":
        await db.update_order(order_id, {"status": "refunded"})
        await db.update_balance(user_id, order["charged_amount"])
        await ctx.bot.send_message(
            user_id,
            msg.OTP_TIMEOUT.format(
                order_id=order_id,
                amount=msg.fmt_money(order["charged_amount"]),
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_home_kb(),
        )


# ---------- cancel ----------


async def cb_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    order_id = q.data.split(":", 1)[1]
    order = await db.get_order(order_id)
    if not order or order.get("status") != "pending":
        await q.edit_message_text(msg.ORDER_NOT_ACTIVE, reply_markup=back_home_kb())
        return
    try:
        await sastaotp.set_status(order["sasta_id"], 8)
    except Exception:
        pass
    await db.update_order(order_id, {"status": "cancelled"})
    await db.update_balance(order["user_id"], order["charged_amount"])
    await q.edit_message_text(
        msg.ORDER_CANCELLED.format(
            order_id=order_id, amount=msg.fmt_money(order["charged_amount"])
        ),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_home_kb(),
    )


# ---------- topup flow (UPI QR) ----------


async def _show_topup(q, ctx):
    kb = [
        [InlineKeyboardButton("₹10", callback_data="amt:10"),
         InlineKeyboardButton("₹20", callback_data="amt:20"),
         InlineKeyboardButton("₹50", callback_data="amt:50")],
        [InlineKeyboardButton("₹100", callback_data="amt:100"),
         InlineKeyboardButton("₹200", callback_data="amt:200"),
         InlineKeyboardButton("₹500", callback_data="amt:500")],
        [InlineKeyboardButton("✏️ Custom Amount", callback_data="amt:custom")],
        [InlineKeyboardButton("🏠 Home", callback_data="menu:home")],
    ]
    m = msg.TOPUP_START.format(upi_id=UPI_ID, upi_name=UPI_NAME)
    await q.edit_message_text(
        m, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(kb)
    )


async def cb_amount(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    choice = q.data.split(":", 1)[1]
    if choice == "custom":
        ctx.user_data["awaiting_amount"] = True
        await q.edit_message_text(
            msg.CUSTOM_AMOUNT_PROMPT,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="menu:topup")]]),
        )
        return
    amount = float(choice)
    await _proceed_to_qr(q, ctx, amount)


async def _proceed_to_qr(q, ctx, amount: float):
    if amount < MIN_TOPUP or amount > MAX_TOPUP:
        await q.edit_message_text(msg.AMOUNT_OUT_OF_RANGE, reply_markup=back_home_kb())
        return
    topup_id = uuid.uuid4().hex[:10]
    ctx.user_data["topup_id"] = topup_id
    ctx.user_data["topup_amount"] = amount
    user_id = q.from_user.id
    await db.create_topup({
        "topup_id": topup_id,
        "user_id": user_id,
        "amount": amount,
        "status": "pending",
        "utr_or_txn": "",
        "created_at": datetime.datetime.utcnow(),
    })
    qr_url = f"{GENQR_BASE}?upi={UPI_ID}&amount={amount}&name={UPI_NAME}"
    text = msg.PAYMENT_INSTRUCTIONS.format(
        amount=msg.fmt_money(amount), upi_id=UPI_ID, upi_name=UPI_NAME
    )
    kb = [
        [InlineKeyboardButton("✅ Deposit Done", callback_data="topup_paid")],
        [InlineKeyboardButton("⬅️ Back", callback_data="menu:topup"),
         InlineKeyboardButton("❌ Cancel", callback_data="topup_cancel")],
    ]
    await q.edit_message_text(
        text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(kb)
    )
    try:
        await q.message.reply_photo(
            photo=qr_url, caption=msg.QR_CAPTION_INLINE.format(amount=msg.fmt_money(amount))
        )
    except Exception as e:
        log.warning("reply_photo failed: %s", e)


async def cb_topup_paid(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not ctx.user_data.get("topup_id"):
        await q.edit_message_text(msg.TOPUP_SESSION_EXPIRED, reply_markup=back_home_kb())
        return
    await q.edit_message_text(
        msg.TOPUP_PAID_PROMPT,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="topup_cancel")]]),
    )
    ctx.user_data["awaiting_utr"] = True


async def cb_topup_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    tid = ctx.user_data.get("topup_id")
    if tid:
        await db.update_topup(tid, {"status": "cancelled"})
    ctx.user_data.pop("topup_id", None)
    ctx.user_data.pop("topup_amount", None)
    ctx.user_data.pop("awaiting_utr", None)
    ctx.user_data.pop("awaiting_amount", None)
    await _show_home(q, await ensure_user(update))


async def verify_payment(mail: str, app_pass: str, ref: str, amount: float) -> dict:
    params = {"mail": mail, "apppass": app_pass, "amount": str(int(amount))}
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(VERIFY_BASE, params={**params, "utr": ref})
        data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        if isinstance(data, dict) and data.get("found"):
            return data
        r = await c.get(VERIFY_BASE, params={**params, "txnid": ref})
        data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        return data if isinstance(data, dict) else {}


# ---------- redeem ----------


async def cb_redeem_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data.pop("awaiting_redeem", None)
    await _show_home(q, await ensure_user(update))


async def _handle_redeem(update: Update, ctx: ContextTypes.DEFAULT_TYPE, code: str):
    user = await ensure_user(update)
    rc = await db.get_redeem_code(code)
    if not rc:
        await update.message.reply_text(msg.REDEEM_INVALID, reply_markup=back_home_kb())
        return
    if rc.get("used_by") is not None:
        await update.message.reply_text(msg.REDEEM_USED, reply_markup=back_home_kb())
        return
    amount = rc.get("amount", 0.0)
    await db.use_redeem_code(code, user["user_id"])
    await db.update_balance(user["user_id"], amount)
    await update.message.reply_text(
        msg.REDEEM_SUCCESS.format(
            amount=msg.fmt_money(amount),
            balance=msg.fmt_money(user.get("balance", 0) + amount),
        ),
        reply_markup=back_home_kb(),
    )


# ---------- text routing (for text input states) ----------


async def text_router(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if ctx.user_data.get("awaiting_amount"):
        ctx.user_data.pop("awaiting_amount", None)
        try:
            amount = float(text.replace("₹", "").replace(",", "").strip())
        except ValueError:
            await update.message.reply_text(msg.INVALID_AMOUNT, reply_markup=back_home_kb())
            return
        await _proceed_to_qr_text(update, ctx, amount)
        return

    if ctx.user_data.get("awaiting_utr"):
        ctx.user_data.pop("awaiting_utr", None)
        ref = text.strip()
        if len(ref) < 4:
            await update.message.reply_text(msg.INVALID_UTR, reply_markup=back_home_kb())
            return
        tid = ctx.user_data.get("topup_id")
        amount = ctx.user_data.get("topup_amount", 0.0)
        if not tid:
            await update.message.reply_text(msg.TOPUP_SESSION_EXPIRED, reply_markup=back_home_kb())
            return
        await update.message.reply_text(msg.VERIFYING)
        try:
            result = await verify_payment(UPI_MAIL, UPI_APP_PASS, ref, amount)
        except Exception as e:
            await update.message.reply_text(msg.VERIFY_ERROR.format(error=e), reply_markup=back_home_kb())
            return
        if isinstance(result, dict) and result.get("found"):
            await db.update_topup(tid, {"status": "completed", "utr_or_txn": ref})
            await db.update_balance(update.effective_user.id, amount)
            user = await db.get_user(update.effective_user.id)
            await update.message.reply_text(
                msg.PAYMENT_VERIFIED.format(
                    amount=msg.fmt_money(amount),
                    ref=ref,
                    balance=msg.fmt_money(user.get("balance", 0)),
                ),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=back_home_kb(),
            )
            await log_to_channel(ctx, msg.CHANNEL_TOPUP_LOG.format(
                username=user.get("username", "—"), user_id=user["user_id"],
                amount=msg.fmt_money(amount), ref=ref,
                balance=msg.fmt_money(user.get("balance", 0)),
                time=datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            ))
        else:
            await db.update_topup(tid, {"status": "failed", "utr_or_txn": ref})
            await update.message.reply_text(
                msg.PAYMENT_NOT_FOUND.format(amount=msg.fmt_money(amount)),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=back_home_kb(),
            )
        return

    if ctx.user_data.get("awaiting_redeem"):
        ctx.user_data.pop("awaiting_redeem", None)
        await _handle_redeem(update, ctx, text.strip())
        return

    await update.message.reply_text(msg.USE_MENU, reply_markup=home_kb(is_admin(update.effective_user.id)))


async def _proceed_to_qr_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE, amount: float):
    if amount < MIN_TOPUP or amount > MAX_TOPUP:
        await update.message.reply_text(msg.AMOUNT_OUT_OF_RANGE, reply_markup=back_home_kb())
        return
    topup_id = uuid.uuid4().hex[:10]
    ctx.user_data["topup_id"] = topup_id
    ctx.user_data["topup_amount"] = amount
    user_id = update.effective_user.id
    await db.create_topup({
        "topup_id": topup_id,
        "user_id": user_id,
        "amount": amount,
        "status": "pending",
        "utr_or_txn": "",
        "created_at": datetime.datetime.utcnow(),
    })
    qr_url = f"{GENQR_BASE}?upi={UPI_ID}&amount={amount}&name={UPI_NAME}"
    text = msg.PAYMENT_INSTRUCTIONS.format(
        amount=msg.fmt_money(amount), upi_id=UPI_ID, upi_name=UPI_NAME
    )
    kb = [
        [InlineKeyboardButton("✅ Deposit Done", callback_data="topup_paid")],
        [InlineKeyboardButton("❌ Cancel", callback_data="topup_cancel")],
    ]
    await update.message.reply_photo(
        photo=qr_url,
        caption=text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(kb),
    )


# ---------- admin commands (text-based, kept as /commands) ----------


async def cmd_addbalance(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = await ensure_user(update)
    if not user.get("is_admin"):
        return
    if len(ctx.args) < 2:
        await update.message.reply_text(msg.ADDBALANCE_USAGE)
        return
    try:
        uid = int(ctx.args[0])
        amt = float(ctx.args[1])
    except ValueError:
        await update.message.reply_text(msg.INVALID_ARGS)
        return
    await db.update_balance(uid, amt)
    await update.message.reply_text(
        msg.ADDBALANCE_DONE.format(amount=msg.fmt_money(amt), user_id=uid)
    )


async def cmd_removebalance(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = await ensure_user(update)
    if not user.get("is_admin"):
        return
    if len(ctx.args) < 2:
        await update.message.reply_text(msg.REMOVEBALANCE_USAGE)
        return
    try:
        uid = int(ctx.args[0])
        amt = float(ctx.args[1])
    except ValueError:
        await update.message.reply_text(msg.INVALID_ARGS)
        return
    await db.update_balance(uid, -amt)
    await update.message.reply_text(
        msg.REMOVEBALANCE_DONE.format(amount=msg.fmt_money(amt), user_id=uid)
    )


async def cmd_setmarkup(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = await ensure_user(update)
    if not user.get("is_admin"):
        return
    if not ctx.args:
        await update.message.reply_text(msg.SETMARKUP_USAGE)
        return
    try:
        pct = float(ctx.args[0])
    except ValueError:
        await update.message.reply_text(msg.INVALID_PERCENT)
        return
    await db.set_setting("markup_pct", pct)
    await update.message.reply_text(msg.SETMARKUP_DONE.format(markup=pct))


async def cmd_users(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = await ensure_user(update)
    if not user.get("is_admin"):
        return
    users = await db.get_all_users()
    lines = [msg.USERS_HEADER.format(count=len(users))]
    for u in users[:50]:
        lines.append(
            msg.USERS_ROW.format(
                user_id=u["user_id"],
                username=u.get("username", "—"),
                balance=msg.fmt_money(u.get("balance", 0)),
            )
        )
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def cmd_orders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = await ensure_user(update)
    if not user.get("is_admin"):
        return
    orders = await db.get_recent_orders(20)
    if not orders:
        await update.message.reply_text(msg.NO_ORDERS_ADMIN)
        return
    lines = [msg.ORDERS_HEADER]
    for o in orders:
        lines.append(
            msg.ORDERS_ROW.format(
                order_id=o["order_id"][:8],
                user_id=o["user_id"],
                service=o["service"],
                status=o["status"],
                amount=msg.fmt_money(o["charged_amount"]),
            )
        )
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def cmd_broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = await ensure_user(update)
    if not user.get("is_admin"):
        return
    if not ctx.args:
        await update.message.reply_text(msg.BROADCAST_USAGE)
        return
    m = " ".join(ctx.args)
    users = await db.get_all_users()
    sent = 0
    for u in users:
        try:
            await ctx.bot.send_message(u["user_id"], msg.BROADCAST_MSG.format(message=m))
            sent += 1
        except Exception:
            pass
    await update.message.reply_text(
        msg.BROADCAST_DONE.format(sent=sent, total=len(users))
    )


async def cmd_profit(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = await ensure_user(update)
    if not user.get("is_admin"):
        return
    cursor = db.orders_col.find({"status": {"$in": ["completed", "refunded"]}})
    total_base = 0.0
    total_charged = 0.0
    count = 0
    async for o in cursor:
        total_base += o.get("base_cost", 0.0)
        total_charged += o.get("charged_amount", 0.0)
        count += 1
    profit = total_charged - total_base
    text = msg.PROFIT_REPORT.format(
        count=count,
        base=msg.fmt_money(total_base),
        charged=msg.fmt_money(total_charged),
        profit=msg.fmt_money(profit),
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_genredeem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = await ensure_user(update)
    if not user.get("is_admin"):
        return
    if not ctx.args:
        await update.message.reply_text(msg.GENREDEEM_USAGE)
        return
    try:
        amount = float(ctx.args[0])
    except ValueError:
        await update.message.reply_text(msg.GENREDEEM_INVALID)
        return
    code = uuid.uuid4().hex[:8].upper()
    await db.redeem_codes_col.insert_one({
        "code": code,
        "amount": amount,
        "used_by": None,
        "created_at": datetime.datetime.utcnow(),
    })
    await update.message.reply_text(
        msg.GENREDEEM_DONE.format(code=code, amount=msg.fmt_money(amount)),
        parse_mode=ParseMode.MARKDOWN,
    )


# ---------- main ----------


async def post_init(app: Application):
    await db.ensure_indexes()
    await load_services()


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN not set in .env")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("addbalance", cmd_addbalance))
    app.add_handler(CommandHandler("removebalance", cmd_removebalance))
    app.add_handler(CommandHandler("setmarkup", cmd_setmarkup))
    app.add_handler(CommandHandler("users", cmd_users))
    app.add_handler(CommandHandler("orders", cmd_orders))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CommandHandler("profit", cmd_profit))
    app.add_handler(CommandHandler("genredeem", cmd_genredeem))

    app.add_handler(CallbackQueryHandler(cb_menu, pattern="^menu:"))
    app.add_handler(CallbackQueryHandler(cb_service, pattern="^svc:"))
    app.add_handler(CallbackQueryHandler(cb_country, pattern="^ctry:"))
    app.add_handler(CallbackQueryHandler(cb_buy_confirm, pattern="^buy_confirm$"))
    app.add_handler(CallbackQueryHandler(cb_buy_cancel, pattern="^buy_cancel$"))
    app.add_handler(CallbackQueryHandler(cb_cancel, pattern="^cancel:"))
    app.add_handler(CallbackQueryHandler(cb_amount, pattern="^amt:"))
    app.add_handler(CallbackQueryHandler(cb_topup_paid, pattern="^topup_paid$"))
    app.add_handler(CallbackQueryHandler(cb_topup_cancel, pattern="^topup_cancel$"))
    app.add_handler(CallbackQueryHandler(cb_redeem_cancel, pattern="^redeem_cancel$"))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    log.info("Starting OTP reseller bot...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
