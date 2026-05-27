import asyncio
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import polars as pl
from rapidfuzz import fuzz

logging.basicConfig(level=logging.INFO)

TOKEN = "8775755021:AAHDhHo1T9NvPNA84nsSgveMB8F5wGQIU2Y"

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
            all_data.append(row)
    except:
        pass

print(f"Loaded {len(all_data)} products")
print("Bot Online Hai")

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    results = []

    for row in all_data:
        try:
            code = str(row['CODE']).strip().lower()
            desc = str(row['DESCRIPTION']).strip().lower()

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
                source = str(row.get('SOURCE', '')).strip()
                code = str(row.get('CODE', '')).strip()
                desc = str(row.get('DESCRIPTION', '')).strip()

                msg += f"📦 Code: {code}\n"
                msg += f"📝 {desc}\n\n"

                if source == 'LIGHTING':
                    # Lighting ke sab prices
                    ewp = str(row.get('EWP', '')).strip()
                    mdp = str(row.get('MDP', '')).strip()
                    sdp = str(row.get('SDP', '')).strip()
                    npp = str(row.get('NPP', '')).strip()
                    nrp = str(row.get('NRP', '')).strip()
                    mrp = str(row.get('MRP', '')).strip()

                    if ewp: msg += f"💡 EWP: Rs.{ewp}\n"
                    if mdp: msg += f"💡 MDP: Rs.{mdp}\n"
                    if sdp: msg += f"💰 SDP: Rs.{sdp}\n"
                    if npp: msg += f"💰 NPP: Rs.{npp}\n"
                    if nrp: msg += f"💰 NRP: Rs.{nrp}\n"
                    if mrp: msg += f"💰 MRP: Rs.{mrp}\n"
                    msg += "🔆 Category: Lighting\n"
                else:
                    # Fittings ke prices
                    sdp = str(row.get('SDP', '')).strip()
                    nrp = str(row.get('NRP', '')).strip()
                    mrp = str(row.get('MRP', '')).strip()
                    old_nrp = str(row.get('OLD_NRP', '')).strip()
                    old_mrp = str(row.get('OLD_MRP', '')).strip()

                    if sdp: msg += f"💰 SDP: Rs.{sdp}\n"
                    if nrp: msg += f"💰 NRP: Rs.{nrp}\n"
                    if mrp: msg += f"💰 MRP: Rs.{mrp}\n"
                    if old_nrp: msg += f"📜 Old NRP: Rs.{old_nrp}\n"
                    if old_mrp: msg += f"📜 Old MRP: Rs.{old_mrp}\n"
                    msg += "🚿 Category: Fittings\n"

                msg += "-----------------------------\n\n"
            except:
                pass
    else:
        msg = "❌ Product nahi mila!\n\nKripya sahi code ya naam likho.\nExample: CHR-079N ya wall light"

    await update.message.reply_text(msg)

async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, reply))
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    print("Polling started...")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
    
