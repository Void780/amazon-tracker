import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

import database
import scraper
from config import BOT_TOKEN, CHECK_INTERVAL

# Log di base per vedere cosa succede nel terminale
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

#Comandi del bot

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Benvenuto su Amazon Price Tracker!* 🛒\n\n"
        "Manda un link Amazon e ti avviso quando il prezzo scende! 🔔\n\n"
        "📌 *Comandi disponibili:*\n"
        "/lista — Vedi i prodotti che stai tracciando\n"
        "/untrack — Rimuovi un prodotto dal tracking\n"
        "/start — Mostra questo messaggio",
        parse_mode="Markdown"
    )

async def lista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    prodotti = database.get_prodotti_utente(user_id)

    if not prodotti:
        await update.message.reply_text(
            "📋 Non stai tracciando nessun prodotto.\n"
            "Manda un link Amazon per iniziare! 🔗"
        )
        return

    testo = "📋 *Prodotti tracciati:*\n\n"
    keyboard = []

    for p in prodotti:
        pid, uid, url, nome, prezzo, aggiornato = p
        prezzo_str = f"€{prezzo:.2f}" if prezzo else "N/D"
        testo += f"📦 *{nome[:60]}*\n💰 Prezzo attuale: {prezzo_str}\n\n"
        keyboard.append([
            InlineKeyboardButton(
                f"🗑 Rimuovi: {nome[:35]}...",
                callback_data=f"rimuovi_{pid}"
            )
        ])

    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(testo, parse_mode="Markdown", reply_markup=markup)

async def untrack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    prodotti = database.get_prodotti_utente(user_id)

    if not prodotti:
        await update.message.reply_text("📋 Non stai tracciando nulla da rimuovere!")
        return

    keyboard = [[InlineKeyboardButton(f"🗑 {p[3][:30]}...", callback_data=f"rimuovi_{p[0]}")] for p in prodotti]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Seleziona il prodotto da smettere di tracciare:", reply_markup=markup)

#  Gestione link amazon

async def gestisci_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    user_id = update.effective_user.id

    if "amazon" not in url.lower():
        await update.message.reply_text("❌ Per favore invia un link Amazon valido!")
        return

    msg = await update.message.reply_text("⏳ Sto cercando il prodotto su Amazon...")

    info = scraper.ottieni_info_prodotto(url)

    if not info:
        await msg.edit_text(
            "❌ Non riesco a raggiungere il prodotto.\n"
            "Amazon a volte blocca le richieste automatiche. Riprova tra poco."
        )
        return

    nome = info["nome"]
    prezzo = info["prezzo"]

    if prezzo:
        database.aggiungi_prodotto(user_id, url, nome, prezzo)
        await msg.edit_text(
            f"✅ *Prodotto aggiunto al tracking!*\n\n"
            f"📦 {nome}\n"
            f"💰 Prezzo attuale: *€{prezzo:.2f}*\n\n"
            f"Ti mando un messaggio appena il prezzo scende! 🔔",
            parse_mode="Markdown"
        )
    else:
        await msg.edit_text(
            f"⚠️ Prodotto trovato ma prezzo non leggibile.\n\n"
            f"📦 {nome}\n\n"
            f"Potrebbe essere temporaneamente non disponibile. Riprova più tardi."
        )

#  Bottoni inline (rimuovi prodotto)


async def gestisci_bottone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("rimuovi_"):
        prodotto_id = int(query.data.split("_")[1])
        database.rimuovi_prodotto(prodotto_id, query.from_user.id)
        await query.edit_message_text("🗑 Prodotto rimosso dal tracking!")


#Controlo automatico dei prezzi

async def controlla_prezzi(context: ContextTypes.DEFAULT_TYPE):
    """Viene eseguita automaticamente ogni CHECK_INTERVAL secondi."""
    print("🔍 Controllo prezzi in corso...")
    prodotti = database.get_tutti_prodotti()

    for p in prodotti:
        pid, user_id, url, nome, prezzo_vecchio, aggiornato = p

        info = scraper.ottieni_info_prodotto(url)
        if not info or not info["prezzo"]:
            continue

        prezzo_nuovo = info["prezzo"]

        # Se il prezzo è sceso → manda notifica
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
                    parse_mode="Markdown",
                    disable_web_page_preview=False
                )
                print(f"✅ Notifica inviata a {user_id} per: {nome}")
            except Exception as e:
                print(f"❌ Errore notifica: {e}")

        # Aggiorna il prezzo nel database
        database.aggiorna_prezzo(pid, prezzo_nuovo)



#  Avvio del bot


def main():
    database.init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lista", lista))
    app.add_handler(CommandHandler("untrack", untrack))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"https?://"), gestisci_link))
    app.add_handler(CallbackQueryHandler(gestisci_bottone))

    # Job periodico per controllare i prezzi
    app.job_queue.run_repeating(controlla_prezzi, interval=CHECK_INTERVAL, first=60)

    print("🤖 Bot avviato! Premi CTRL+C per fermarlo.")
    app.run_polling()


if __name__ == "__main__":
    main()