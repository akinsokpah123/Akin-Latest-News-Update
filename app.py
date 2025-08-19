import os
import requests
import sqlite3
from flask import Flask, render_template_string, request
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

# Load API key
API_KEY = os.getenv("NEWS_API_KEY")

app = Flask(__name__)
DB_FILE = "news.db"

# HTML template
HTML_CODE = """
<!DOCTYPE html>
<html>
<head>
    <title>Global News Daily</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; margin:0; padding:0; background: #f4f4f4; }
        header { background: #333; color: white; padding: 10px 0; text-align: center; }
        #search { margin: 20px auto; display: flex; justify-content: center; }
        #search input { padding: 10px; width: 50%; border-radius: 5px; border: 1px solid #ccc; }
        #search button { padding: 10px; border: none; border-radius: 5px; background: #4CAF50; color: white; cursor: pointer; }
        #search button:hover { background: #45a049; }
        #articles { width: 80%; margin: 20px auto; }
        .article { background: white; margin-bottom: 15px; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .article h2 { margin: 0; font-size: 20px; }
        .article p { margin: 10px 0; }
        .article a { text-decoration: none; color: #333; }
        .article a:hover { color: #4CAF50; }
    </style>
</head>
<body>
    <header>
        <h1>🌍 Global News Daily</h1>
    </header>

    <div id="search">
        <form method="get" action="/">
            <input type="text" name="q" placeholder="Search news..." value="{{ query }}">
            <button type="submit">Search</button>
        </form>
    </div>

    <div id="articles">
        {% for article in articles %}
        <div class="article">
            <h2><a href="{{ article.url }}" target="_blank">{{ article.title }}</a></h2>
            <p>{{ article.description or "No description available." }}</p>
            <small>Source: {{ article.source }}</small>
        </div>
        {% endfor %}
        {% if not articles %}
            <p>No articles found.</p>
        {% endif %}
    </div>
</body>
</html>
"""

# Initialize database
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            url TEXT,
            source TEXT,
            published_at TEXT
        )
    """)
    conn.commit()
    conn.close()

# Fetch news from API
def fetch_news_api():
    url = "https://newsapi.org/v2/top-headlines"
    params = {
        "apiKey": API_KEY,
        "language": "en",
        "pageSize": 50,
        "country": "us"
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        return data.get("articles", [])
    except Exception as e:
        print("API fetch error:", e)
        return []

# Save news to SQLite
def save_news_to_db():
    articles = fetch_news_api()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    for article in articles:
        cursor.execute("""
            INSERT INTO news (title, description, url, source, published_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            article.get("title"),
            article.get("description"),
            article.get("url"),
            article.get("source", {}).get("name"),
            article.get("publishedAt")
        ))
    conn.commit()
    conn.close()
    print(f"{len(articles)} articles saved to database at {datetime.now()}")

# Fetch news from SQLite
def get_news_from_db(query=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    if query:
        cursor.execute("SELECT title, description, url, source FROM news WHERE title LIKE ? OR description LIKE ? ORDER BY id DESC", (f"%{query}%", f"%{query}%"))
    else:
        cursor.execute("SELECT title, description, url, source FROM news ORDER BY id DESC LIMIT 20")
    rows = cursor.fetchall()
    conn.close()
    return [{"title": r[0], "description": r[1], "url": r[2], "source": r[3]} for r in rows]

@app.route("/")
def home():
    query = request.args.get("q")
    articles = get_news_from_db(query)
    return render_template_string(HTML_CODE, articles=articles, query=query or "")

@app.route("/healthz")
def healthz():
    return "ok", 200

# Scheduler to update news every day at midnight
scheduler = BackgroundScheduler()
scheduler.add_job(save_news_to_db, "interval", hours=24)
scheduler.start()

if __name__ == "__main__":
    init_db()
    save_news_to_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
