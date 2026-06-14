import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

import database
import scraper
from config import BOT_TOKEN, CHECK_INTERVAL

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Benvenuto su Amazon Price Tracker!* 🛒\n\n"
        "Manda un link Amazon e ti avviso quando il prezzo scende! 🔔\n\n"
        "📌 *Comandi:*\n"
        "/lista — Vedi i prodotti tracciati\n"
        "/untrack — Rimuovi un prodotto dal tracking\n"
        "/start — Mostra questo messaggio",
        parse_mode="Markdown"
    )

async def lista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    prodotti = database.get_prodotti_utente(user_id)

    if not prodotti:
        await update.message.reply_text("📋 Non stai tracciando nessun prodotto.\nManda un link Amazon per iniziare!")
        return

    testo = "📋 *Prodotti tracciati:*\n\n"
    keyboard = []

    for p in prodotti:
        pid, uid, url, nome, prezzo, aggiornato = p
        prezzo_str = f"€{prezzo:.2f}" if prezzo else "N/D"
        testo += f"📦 *{nome[:60]}*\n💰 {prezzo_str}\n\n"
        keyboard.append([InlineKeyboardButton(f"🗑 Rimuovi: {nome[:35]}...", callback_data=f"rimuovi_{pid}")])

    await update.message.reply_text(testo, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def untrack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    prodotti = database.get_prodotti_utente(user_id)

    if not prodotti:
        await update.message.reply_text("📋 Non stai tracciando nulla da rimuovere!")
        return

    keyboard = [[InlineKeyboardButton(f"🗑 {p[3][:40]}...", callback_data=f"rimuovi_{p[0]}")] for p in prodotti]
    await update.message.reply_text("Seleziona il prodotto da rimuovere:", reply_markup=InlineKeyboardMarkup(keyboard))

async def gestisci_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    user_id = update.effective_user.id

    if "amazon" not in url.lower():
        await update.message.reply_text("❌ Per favore invia un link Amazon valido!")
        return

    msg = await update.message.reply_text("⏳ Sto cercando il prodotto su Amazon...")
    info = scraper.ottieni_info_prodotto(url)

    if not info:
        await msg.edit_text("❌ Non riesco a raggiungere il prodotto. Riprova tra poco.")
        return

    nome = info["nome"]
    prezzo = info["prezzo"]

    if prezzo:
        database.aggiungi_prodotto(user_id, url, nome, prezzo)
        await msg.edit_text(
            f"✅ *Prodotto aggiunto!*\n\n"
            f"📦 {nome}\n"
            f"💰 Prezzo attuale: *€{prezzo:.2f}*\n\n"
            f"Ti avviso appena scende! 🔔",
            parse_mode="Markdown"
        )
    else:
        await msg.edit_text(f"⚠️ Prodotto trovato ma prezzo non leggibile.\n\n📦 {nome}\n\nRiprova più tardi.")

async def gestisci_bottone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith("rimuovi_"):
        prodotto_id = int(query.data.split("_")[1])
        database.rimuovi_prodotto(prodotto_id, query.from_user.id)
        await query.edit_message_text("🗑 Prodotto rimosso!")

async def controlla_prezzi(context: ContextTypes.DEFAULT_TYPE):
    prodotti = database.get_tutti_prodotti()
    for p in prodotti:
        pid, user_id, url, nome, prezzo_vecchio, aggiornato = p
        info = scraper.ottieni_info_prodotto(url)
        if not info or not info["prezzo"]:
            continue
        prezzo_nuovo = info["prezzo"]
        if prezzo_vecchio and prezzo_nuovo < prezzo_vecchio:
            risparmio = prezzo_vecchio - prezzo_nuovo
            percentuale = (risparmio / prezzo_vecchio) * 100
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"🔥 *PREZZO SCESO!*\n\n"
                        f"📦 {nome}\n\n"
                        f"💸 Prima: €{prezzo_vecchio:.2f}\n"
                        f"✅ Ora: *€{prezzo_nuovo:.2f}*\n"
                        f"💰 Risparmi: €{risparmio:.2f} (-{percentuale:.0f}%)\n\n"
                        f"🛒 [Vai all'offerta]({url})"
                    ),
                    parse_mode="Markdown"
                )
            except Exception as e:
                print(f"Errore notifica: {e}")
        database.aggiorna_prezzo(pid, prezzo_nuovo)

def main():
    database.init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lista", lista))
    app.add_handler(CommandHandler("untrack", untrack))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"https?://"), gestisci_link))
    app.add_handler(CallbackQueryHandler(gestisci_bottone))
    app.job_queue.run_repeating(controlla_prezzi, interval=CHECK_INTERVAL, first=60)
    print("🤖 Bot avviato!")
    app.run_polling()

if __name__ == "__main__":
    main()
