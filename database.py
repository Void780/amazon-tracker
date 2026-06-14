import sqlite3

DB_PATH = "tracker.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS prodotti (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            url         TEXT NOT NULL,
            nome        TEXT,
            prezzo      REAL,
            aggiornato  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def aggiungi_prodotto(user_id, url, nome, prezzo):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO prodotti (user_id, url, nome, prezzo) VALUES (?, ?, ?, ?)",
        (user_id, url, nome, prezzo)
    )
    conn.commit()
    conn.close()

def get_prodotti_utente(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM prodotti WHERE user_id = ?", (user_id,))
    prodotti = c.fetchall()
    conn.close()
    return prodotti

def get_tutti_prodotti():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM prodotti")
    prodotti = c.fetchall()
    conn.close()
    return prodotti

def aggiorna_prezzo(prodotto_id, nuovo_prezzo):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "UPDATE prodotti SET prezzo = ?, aggiornato = CURRENT_TIMESTAMP WHERE id = ?",
        (nuovo_prezzo, prodotto_id)
    )
    conn.commit()
    conn.close()

def rimuovi_prodotto(prodotto_id, user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "DELETE FROM prodotti WHERE id = ? AND user_id = ?",
        (prodotto_id, user_id)
    )
    conn.commit()
    conn.close()
