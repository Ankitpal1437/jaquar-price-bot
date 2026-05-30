import asyncio
import logging
import os
from aiohttp import web
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import polars as pl
from rapidfuzz import fuzz

logging.basicConfig(level=logging.INFO)

TOKEN = "8775755021:AAHDhHo1T9NvPNA84nsSgveMB8F5wGQIU2Y"
PORT = int(os.environ.get("PORT", 10000))
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://jaquar-price-bot.onrender.com")

# CSV LOAD
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
        if old_nrp and old_nrp not in ['None','nan','-','']: msg += f"📜 Old NRP: Rs.{old_nrp}\n"
        if old_mrp and old_mrp not in ['None','nan','-','']: msg += f"📜 Old MRP: Rs.{old_mrp}\n"
        msg += f"🚿 Category: Fittings\n"

    msg += "-----------------------------\n\n"
    return msg

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    text_lower = text.lower()

    exact_match = []      # Bilkul same code
    starts_with = []      # Code jo text se start hota hai
    contains_code = []    # Code mein text hai
    desc_match = []       # Description mein text hai

    for row in all_data:
        code = str(row.get('CODE', '')).strip()
        code_lower = code.lower()
        desc_lower = str(row.get('DESCRIPTION', '')).strip().lower()

        if code_lower == text_lower:
            exact_match.append(row)
        elif code_lower.startswith(text_lower):
            starts_with.append(row)
        elif text_lower in code_lower:
            contains_code.append(row)
        elif text_lower in desc_lower:
            desc_match.append(row)

    # Priority: exact → starts_with → contains → desc
    results = exact_match + starts_with + contains_code + desc_match

    if results:
        total = len(results)
        show = results[:5]
        msg = f"🔍 *{total} product(s) mila*\n\n"
        if total > 5:
            msg += f"_(Top 5 dikh rahe hain)_\n\n"
        for row in show:
            msg += format_product(row)
    else:
        msg = (
            "❌ *Product nahi mila!*\n\n"
            "💡 Tips:\n"
            "• Exact code try karo: `AQT-CHR-3057P`\n"
            "• Part of code: `3057P`\n"
            "• Product naam: `angle cock`\n"
            "• Series: `GRF` ya `CHR`"
        )

    await update.message.reply_text(msg, parse_mode="Markdown")

async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, reply))

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
        return web.Response(text="Jaquar Bot is Running! 🚿")

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
    
