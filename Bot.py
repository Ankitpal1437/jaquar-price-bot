import asyncio
import logging
import os
import json
from datetime import datetime
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, CallbackQueryHandler, filters, ContextTypes
import polars as pl
from rapidfuzz import fuzz

logging.basicConfig(level=logging.INFO)

TOKEN = "8775755021:AAHDhHo1T9NvPNA84nsSgveMB8F5wGQIU2Y"
PORT = int(os.environ.get("PORT", 10000))
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://jaquar-price-bot.onrender.com")

# =====================
# ADMIN CONFIG
# =====================
# Apna Telegram User ID daalo — ye tumhara admin ID hai
# Apna ID jaanne ke liye @userinfobot pe /start bhejo Telegram mein
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

# Allowed users ka set — sirf inhe access milega
# Khali hone par SIRF ADMIN access kar sakta hai
allowed_users = set()

# Search logs
search_logs = []

# Pending requests — jo log access maang rahe hain
pending_requests = {}

# =====================
# CSV LOAD
# =====================
df = pl.read_csv("price.csv", infer_schema_length=0)
all_data = []
for row in df.iter_rows(named=True):
    try:
        code = str(row.get('CODE', '')).strip()
        desc = str(row.get('DESCRIPTION', '')).strip()
        if len(code) > 2 and len(desc) > 2 and code != 'CODE':
            all_data.append(row)
    except:
        pass

print(f"Loaded {len(all_data)} products")
print("Bot Online Hai")

# =====================
# SEARCH LOGIC
# =====================
def search_products(text):
    text = text.strip().lower()
    exact = []
    ends_with = []
    starts_with = []
    contains_code = []
    contains_desc = []
    fuzzy = []

    for row in all_data:
        try:
            code = str(row.get('CODE', '')).strip().lower()
            desc = str(row.get('DESCRIPTION', '')).strip().lower()

            if text == code:
                exact.append(row)
            elif code.endswith(text):
                ends_with.append(row)
            elif code.startswith(text):
                starts_with.append(row)
            elif text in code:
                idx = code.find(text)
                after = code[idx+len(text):]
                if after == '' or after.startswith('-'):
                    ends_with.append(row)
                else:
                    contains_code.append(row)
            elif text in desc:
                contains_desc.append(row)
            else:
                score = fuzz.partial_ratio(text, code)
                if score > 88:
                    fuzzy.append((score, row))
        except:
            pass

    fuzzy_sorted = [r for _, r in sorted(fuzzy, key=lambda x: -x[0])]
    final = exact + ends_with + starts_with + contains_code + contains_desc + fuzzy_sorted

    seen = set()
    unique = []
    for r in final:
        c = str(r.get('CODE', ''))
        if c not in seen:
            seen.add(c)
            unique.append(r)
    return unique

# =====================
# FORMAT PRODUCT
# =====================
def format_product(row):
    code = str(row.get('CODE', '')).strip()
    desc = str(row.get('DESCRIPTION', '')).strip()
    sdp = str(row.get('SDP', '')).strip()
    nrp = str(row.get('NRP', '')).strip()
    mrp = str(row.get('MRP', '')).strip()
    old_nrp = str(row.get('OLD_NRP', '')).strip()
    old_mrp = str(row.get('OLD_MRP', '')).strip()
    source = str(row.get('SOURCE', '')).strip()

    msg = f"📦 Code: {code}\n"
    msg += f"📝 {desc}\n\n"

    if source == 'LIGHTING':
        ewp = str(row.get('EWP', '')).strip()
        mdp = str(row.get('MDP', '')).strip()
        npp = str(row.get('NPP', '')).strip()
        if ewp and ewp not in ['None','nan','']: msg += f"💡 EWP: Rs.{ewp}\n"
        if mdp and mdp not in ['None','nan','']: msg += f"💡 MDP: Rs.{mdp}\n"
        if sdp and sdp not in ['None','nan','']: msg += f"💰 SDP: Rs.{sdp}\n"
        if npp and npp not in ['None','nan','']: msg += f"💰 NPP: Rs.{npp}\n"
        if nrp and nrp not in ['None','nan','']: msg += f"💰 NRP: Rs.{nrp}\n"
        if mrp and mrp not in ['None','nan','']: msg += f"💰 MRP: Rs.{mrp}\n"
        msg += f"🔆 Category: Lighting\n"
    else:
        if sdp and sdp not in ['None','nan','']: msg += f"💰 SDP: Rs.{sdp}\n"
        if nrp and nrp not in ['None','nan','']: msg += f"💰 NRP: Rs.{nrp}\n"
        if mrp and mrp not in ['None','nan','']: msg += f"💰 MRP: Rs.{mrp}\n"
        if old_nrp and old_nrp not in ['None','nan','']: msg += f"📜 Old NRP: Rs.{old_nrp}\n"
        if old_mrp and old_mrp not in ['None','nan','']: msg += f"📜 Old MRP: Rs.{old_mrp}\n"
        msg += f"🚿 Category: Fittings\n"

    msg += "-----------------------------\n\n"
    return msg

# =====================
# ADMIN COMMANDS
# =====================
async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name

    # Agar admin hai
    if user_id == ADMIN_ID:
        msg = f"""👑 *Admin Panel — MST Jaquar Bot*

Tumhara ID: `{user_id}`

*Commands:*
/users — Allowed users list
/pending — Access requests
/logs — Recent search logs
/stats — Bot statistics
/allow <user_id> — User ko access do
/block <user_id> — User ka access hatao
/broadcast <message> — Sabko message bhejo"""
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    # Agar already allowed
    if user_id in allowed_users:
        await update.message.reply_text(
            f"✅ Namaste {username}!\n\n"
            "Jaquar Price Bot mein aapka swagat hai 🚿\n\n"
            "Product code ya naam likho — price mil jayegi!\n\n"
            "Example: *CHR-079N* ya *basin mixer*",
            parse_mode="Markdown"
        )
        return

    # Naya user — access request
    if ADMIN_ID == 0:
        # Admin set nahi hai — sab allowed
        allowed_users.add(user_id)
        await update.message.reply_text(
            f"✅ Namaste {username}! Bot use karne ke liye ready hain.\n\nProduct code likho!"
        )
        return

    # Access request admin ko bhejo
    pending_requests[user_id] = {
        "name": username,
        "full_name": update.effective_user.full_name,
        "time": datetime.now().strftime("%d/%m %H:%M")
    }

    # Admin ko notify karo
    keyboard = [
        [
            InlineKeyboardButton(f"✅ Allow {username}", callback_data=f"allow_{user_id}"),
            InlineKeyboardButton(f"❌ Block", callback_data=f"block_{user_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🔔 *Naya Access Request!*\n\n"
                 f"👤 Naam: {update.effective_user.full_name}\n"
                 f"🔑 Username: @{username}\n"
                 f"🆔 User ID: `{user_id}`\n"
                 f"🕐 Time: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    except:
        pass

    await update.message.reply_text(
        f"⏳ Namaste {update.effective_user.full_name}!\n\n"
        "Aapka access request admin ko bhej diya gaya hai.\n"
        "Thodi der mein approve ho jayega! 🙏"
    )

async def cmd_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not allowed_users:
        await update.message.reply_text("Koi allowed user nahi abhi tak.")
        return
    msg = f"👥 *Allowed Users ({len(allowed_users)}):*\n\n"
    for uid in allowed_users:
        msg += f"• `{uid}`\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def cmd_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not search_logs:
        await update.message.reply_text("Koi search log nahi abhi tak.")
        return
    msg = "📊 *Recent Searches (Last 20):*\n\n"
    for log in search_logs[-20:]:
        msg += f"👤 {log['name']} | 🔍 `{log['query']}` | 📦 {log['results']} results | 🕐 {log['time']}\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    today = datetime.now().strftime("%d/%m/%Y")
    today_searches = [l for l in search_logs if l['time'].startswith(today)]
    unique_users = len(set(l['user_id'] for l in search_logs))
    msg = f"""📊 *Bot Statistics*

👥 Total allowed users: {len(allowed_users)}
🔍 Total searches: {len(search_logs)}
📅 Aaj ke searches: {len(today_searches)}
👤 Unique users: {unique_users}
📦 Total products: {len(all_data)}"""
    await update.message.reply_text(msg, parse_mode="Markdown")

async def cmd_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not pending_requests:
        await update.message.reply_text("Koi pending request nahi.")
        return
    for uid, info in pending_requests.items():
        keyboard = [[
            InlineKeyboardButton("✅ Allow", callback_data=f"allow_{uid}"),
            InlineKeyboardButton("❌ Block", callback_data=f"block_{uid}")
        ]]
        await update.message.reply_text(
            f"⏳ *Pending Request*\n\n"
            f"Naam: {info['full_name']}\n"
            f"ID: `{uid}`\n"
            f"Time: {info['time']}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

async def cmd_allow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Usage: /allow <user_id>")
        return
    uid = int(context.args[0])
    allowed_users.add(uid)
    if uid in pending_requests:
        del pending_requests[uid]
    await update.message.reply_text(f"✅ User `{uid}` ko access de diya!", parse_mode="Markdown")
    try:
        await context.bot.send_message(chat_id=uid, text="✅ Aapka access approve ho gaya! Ab product search kar sakte hain 🚿\n\nExample: CHR-079N")
    except:
        pass

async def cmd_block(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Usage: /block <user_id>")
        return
    uid = int(context.args[0])
    allowed_users.discard(uid)
    if uid in pending_requests:
        del pending_requests[uid]
    await update.message.reply_text(f"🚫 User `{uid}` block kar diya!", parse_mode="Markdown")

async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    msg = ' '.join(context.args)
    success = 0
    for uid in allowed_users:
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 *MST Jaquar Bot:*\n\n{msg}", parse_mode="Markdown")
            success += 1
        except:
            pass
    await update.message.reply_text(f"✅ {success} users ko message bhej diya!")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    data = query.data
    if data.startswith("allow_"):
        uid = int(data.split("_")[1])
        allowed_users.add(uid)
        info = pending_requests.get(uid, {})
        if uid in pending_requests:
            del pending_requests[uid]
        await query.edit_message_text(f"✅ User `{uid}` ({info.get('name','')}) ko access de diya!", parse_mode="Markdown")
        try:
            await context.bot.send_message(chat_id=uid, text="✅ Aapka access approve ho gaya!\n\nAb product search karo 🚿\nExample: CHR-079N")
        except:
            pass
    elif data.startswith("block_"):
        uid = int(data.split("_")[1])
        if uid in pending_requests:
            del pending_requests[uid]
        await query.edit_message_text(f"🚫 User `{uid}` ko block kar diya!")

# =====================
# MAIN SEARCH HANDLER
# =====================
async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name

    # Access check
    if ADMIN_ID != 0 and user_id != ADMIN_ID and user_id not in allowed_users:
        await update.message.reply_text(
            "🔒 Aapko access nahi hai.\n\n/start karo access request ke liye!"
        )
        return

    text = update.message.text.strip()
    if text.startswith('/'):
        return

    results = search_products(text)

    # Log karo
    search_logs.append({
        "user_id": user_id,
        "name": username,
        "query": text,
        "results": len(results),
        "time": datetime.now().strftime("%d/%m/%Y %H:%M")
    })
    # Sirf last 1000 logs rakhenge
    if len(search_logs) > 1000:
        search_logs.pop(0)

    if results:
        total = len(results)
        show = results[:5]
        msg = f"🔍 {total} product(s) mila\n"
        if total > 5:
            msg += f"_(Top 5 dikh rahe hain)_\n"
        msg += "\n"
        for row in show:
            msg += format_product(row)
        if total > 5:
            msg += f"💡 Aur {total-5} products hain — zyada specific code likho!"
    else:
        msg = "❌ Product nahi mila!\n\nKripya sahi code ya naam likho.\nExample: ALD-CHR-079N"

    await update.message.reply_text(msg)

# =====================
# MAIN
# =====================
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", admin_start))
    app.add_handler(CommandHandler("users", cmd_users))
    app.add_handler(CommandHandler("logs", cmd_logs))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("pending", cmd_pending))
    app.add_handler(CommandHandler("allow", cmd_allow))
    app.add_handler(CommandHandler("block", cmd_block))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))

    webhook_path = f"/webhook/{TOKEN}"
    full_webhook_url = f"{WEBHOOK_URL}{webhook_path}"

    await app.initialize()
    await app.bot.set_webhook(url=full_webhook_url, drop_pending_updates=True)

    async def handle_webhook(request):
        data = await request.json()
        update = Update.de_json(data, app.bot)
        await app.process_update(update)
        return web.Response(text="OK")

    async def handle_health(request):
        return web.Response(text="Jaquar Bot is Running!")

    web_app = web.Application()
    web_app.router.add_post(webhook_path, handle_webhook)
    web_app.router.add_get("/", handle_health)
    web_app.router.add_get("/health", handle_health)

    await app.start()
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    print(f"Webhook: {full_webhook_url}")
    print(f"Port: {PORT}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
