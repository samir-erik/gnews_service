from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
import sqlite3
import threading
import schedule
import time

app = Flask(__name__)
CORS(app)

# SUA CHAVE GNEWS
API_KEY = "aa931769f8c1dedc3520ae0756e13fca"

# categorias coletadas automaticamente
CATEGORIAS = [
    "general",
    "technology",
    "business",
    "sports",
    "science",
    "health"
]

# -------------------------
# PAGINA INICIAL
# -------------------------

@app.route("/")
def home():
    return render_template("index.html")


# -------------------------
# CRIAR BANCO
# -------------------------

def criar_banco():

    conn = sqlite3.connect("noticias.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS noticias(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        manchete TEXT,
        resumo TEXT,
        autor TEXT,
        data_publicacao TEXT,
        link TEXT UNIQUE,
        fonte TEXT,
        imagem TEXT,
        categoria TEXT,
        data_coleta DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


# -------------------------
# SALVAR NOTICIA
# -------------------------

def salvar_noticia(noticia):

    conn = sqlite3.connect("noticias.db")
    cursor = conn.cursor()

    try:

        cursor.execute("""
        INSERT INTO noticias
        (manchete,resumo,autor,data_publicacao,link,fonte,imagem,categoria)
        VALUES (?,?,?,?,?,?,?,?)
        """,(
            noticia["manchete"],
            noticia["resumo"],
            noticia["autor"],
            noticia["data"],
            noticia["link"],
            noticia["fonte"],
            noticia["imagem"],
            noticia["categoria"]
        ))

        conn.commit()

    except sqlite3.IntegrityError:
        pass

    conn.close()


# -------------------------
# COLETAR NOTICIAS
# -------------------------

def coletar_noticias():

    print("🔎 Coletando notícias...")

    for categoria in CATEGORIAS:

        url = f"https://gnews.io/api/v4/top-headlines?category={categoria}&lang=pt&apikey={API_KEY}"

        response = requests.get(url)
        dados = response.json()

        if "articles" in dados:

            for item in dados["articles"]:

                noticia = {
                    "manchete": item.get("title"),
                    "resumo": item.get("description"),
                    "autor": item.get("author"),
                    "data": item.get("publishedAt"),
                    "link": item.get("url"),
                    "fonte": item["source"]["name"],
                    "imagem": item.get("image"),
                    "categoria": categoria
                }

                salvar_noticia(noticia)

    print("✅ Coleta finalizada")


# -------------------------
# BOT AUTOMATICO
# -------------------------

def iniciar_bot():

    schedule.every(1).hours.do(coletar_noticias)

    while True:
        schedule.run_pending()
        time.sleep(60)


# -------------------------
# PEGAR NOTICIAS
# -------------------------

@app.route("/get_news")

def get_news():

    busca = request.args.get("busca","")

    conn = sqlite3.connect("noticias.db")
    cursor = conn.cursor()

    if busca:

        cursor.execute("""

        SELECT manchete,resumo,autor,data_publicacao,link,fonte,imagem
        FROM noticias
        WHERE manchete LIKE ?
        OR resumo LIKE ?
        OR fonte LIKE ?
        ORDER BY data_publicacao DESC
        LIMIT 50

        """,('%'+busca+'%','%'+busca+'%','%'+busca+'%',))

    else:

        cursor.execute("""

        SELECT manchete,resumo,autor,data_publicacao,link,fonte,imagem
        FROM noticias
        ORDER BY data_publicacao DESC
        LIMIT 50

        """)

    dados = cursor.fetchall()

    conn.close()

    noticias = []

    for n in dados:

        noticias.append({
            "manchete": n[0],
            "resumo": n[1],
            "autor": n[2],
            "data": n[3],
            "link": n[4],
            "fonte": n[5],
            "imagem": n[6]
        })

    return jsonify(noticias)


# -------------------------
# RANKING FONTES
# -------------------------

@app.route("/ranking")

def ranking():

    conn = sqlite3.connect("noticias.db")
    cursor = conn.cursor()

    cursor.execute("""

    SELECT fonte, COUNT(*) as total
    FROM noticias
    GROUP BY fonte
    ORDER BY total DESC
    LIMIT 10

    """)

    dados = cursor.fetchall()

    conn.close()

    ranking = []

    for r in dados:

        ranking.append({
            "fonte": r[0],
            "total": r[1]
        })

    return jsonify(ranking)


# -------------------------
# DASHBOARD ADMIN
# -------------------------

@app.route("/stats")

def stats():

    conn = sqlite3.connect("noticias.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM noticias")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT fonte) FROM noticias")
    fontes = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT categoria) FROM noticias")
    categorias = cursor.fetchone()[0]

    conn.close()

    return jsonify({
        "total_noticias": total,
        "fontes": fontes,
        "categorias": categorias
    })


# -------------------------
# INICIAR SISTEMA
# -------------------------

if __name__ == "__main__":

    criar_banco()

    coletar_noticias()

    bot = threading.Thread(target=iniciar_bot)
    bot.start()

    app.run(host="0.0.0.0", port=10000)