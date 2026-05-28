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
        vals = list(row.values())
        code = str(vals[0]).strip()
        desc = str(vals[1]).strip()
        if len(code) > 2 and len(desc) > 2:
            all_data.append(vals)
    except:
        pass

print(f"Loaded {len(all_data)} products")
print("Bot Online Hai")

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    results = []
    for row in all_data:
        try:
            code = str(row[0]).strip().lower()
            desc = str(row[1]).strip().lower()
            if text == code:
                results.append(row)
            elif text in desc:
                results.append(row)
            elif text in code:
                results.append(row)
            else:
                score = fuzz.ratio(text, code)
                if score > 92:
                    results.append(row)
        except:
            pass

    if results:
        msg = "🔍 Products Found\n\n"
        for row in results[:5]:
            try:
                msg += f"📦 Code: {row[0]}\n"
                msg += f"📝 {row[1]}\n\n"
                msg += f"💰 SDP: Rs.{row[2]}\n"
                msg += f"💰 NRP: Rs.{row[3]}\n"
                msg += f"💰 MRP: Rs.{row[4]}\n\n"
                msg += f"📜 Old NRP: Rs.{row[5]}\n"
                msg += f"📜 Old MRP: Rs.{row[6]}\n"
                msg += "-----------------------------\n\n"
            except:
                pass
    else:
        msg = "❌ Product nahi mila!\n\nKripya sahi code ya naam likho.\nExample: CHR-079N"

    await update.message.reply_text(msg)

async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, reply))

    # Webhook setup
    webhook_path = f"/webhook/{TOKEN}"
    full_webhook_url = f"{WEBHOOK_URL}{webhook_path}"

    await app.initialize()
    await app.bot.set_webhook(url=full_webhook_url, drop_pending_updates=True)

    # aiohttp web server
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

    print(f"Webhook set: {full_webhook_url}")
    print(f"Server running on port {PORT}")

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
