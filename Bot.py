import asyncio
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import polars as pl
from rapidfuzz import fuzz

logging.basicConfig(level=logging.INFO)

TOKEN = "8862234704:AAFznYQd_ArcV_bwjo4dMFBVxEnVnLkonOY"

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Jaquar Price Bot is Running!")
    def log_message(self, format, *args):
        pass

def run_server():
    server = HTTPServer(("0.0.0.0", 10000), Handler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

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
                msg += "➖➖➖➖➖➖➖➖➖➖\n\n"
            except:
                pass
    else:
        msg = "❌ Product nahi mila!\n\nKripya sahi code ya naam likho.\nExample: CHR-079N"

    await update.message.reply_text(msg)

async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, reply))
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    print("Polling started...")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
    
