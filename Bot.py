from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import pandas as pd
from rapidfuzz import fuzz

# =========================
# TELEGRAM TOKEN
# =========================
TOKEN = "8862234704:AAHoq9-GtNh5RwGx0VRlkXecHdlxzlv1r7g"

# =========================
# CSV FILE LOAD
# =========================
df = pd.read_csv("price.csv", dtype=str)
df = df.fillna("")

all_data = []
for index, row in df.iterrows():
    try:
        code = str(row.iloc[0]).strip()
        desc = str(row.iloc[1]).strip()
        if len(code) > 2 and len(desc) > 2:
            all_data.append(row)
    except:
        pass

print(f"Loaded {len(all_data)} products")
print("Bot Online Hai")

# =========================
# BOT REPLY FUNCTION
# =========================
async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip().lower()
    results = []

    for row in all_data:
        try:
            code = str(row.iloc[0]).strip().lower()
            desc = str(row.iloc[1]).strip().lower()

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
        msg = "Products Found\n\n"
        for row in results[:5]:
            try:
                msg += f"Code: {row.iloc[0]}\n"
                msg += f"Description: {row.iloc[1]}\n"
                msg += f"SDP: Rs.{row.iloc[2]}\n"
                msg += f"NRP: Rs.{row.iloc[3]}\n"
                msg += f"MRP: Rs.{row.iloc[4]}\n"
                msg += f"Old NRP: Rs.{row.iloc[5]}\n"
                msg += f"Old MRP: Rs.{row.iloc[6]}\n"
                msg += "-----------------------------\n\n"
            except:
                pass
    else:
        msg = "Product nahi mila. Kripya sahi code ya naam likho."

    await update.message.reply_text(msg)

# =========================
# START BOT
# =========================
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT, reply))
app.run_polling()
