from flask import (
    Flask, render_template, request,
    redirect, session, send_from_directory, jsonify
)
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "secret123"

SONGS_FOLDER = "static/songs"
DB_NAME = "users.db"


# ---------- DATABASE ----------
def get_db():
    return sqlite3.connect(DB_NAME)


# ---------- AUTH ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()
        cur = db.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT,
                password TEXT
            )
        """)

        cur.execute(
            "INSERT INTO users VALUES (?, ?)",
            (username, password)
        )

        db.commit()
        db.close()
        return redirect('/login')

    return render_template("register.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()
        cur = db.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT,
                password TEXT
            )
        """)

        cur.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        )

        user = cur.fetchone()
        db.close()

        if user:
            session['user'] = username
            return redirect('/')
        else:
            error = "Invalid username or password"

    return render_template("login.html", error=error)


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')


# ---------- MAIN ----------
@app.route('/')
def index():
    if 'user' not in session:
        return redirect('/login')

    search = request.args.get('search', '').lower()

    songs = os.listdir(SONGS_FOLDER)
    if search:
        songs = [s for s in songs if search in s.lower()]

    db = get_db()
    cur = db.cursor()

    # Playlist table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS playlist (
            username TEXT,
            song TEXT
        )
    """)

    # Recently played table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS recently_played (
            username TEXT,
            song TEXT,
            played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Fetch playlist
    cur.execute(
        "SELECT song FROM playlist WHERE username=?",
        (session['user'],)
    )
    playlist = [row[0] for row in cur.fetchall()]

    # Fetch recently played (last 5)
    cur.execute("""
        SELECT song FROM recently_played
        WHERE username=?
        ORDER BY played_at DESC
        LIMIT 5
    """, (session['user'],))
    recent = [row[0] for row in cur.fetchall()]

    db.close()

    return render_template(
        "index.html",
        songs=songs,
        playlist=playlist,
        recent=recent,
        user=session['user'],
        search=search
    )


# ---------- PLAYLIST API ----------
@app.route('/add_to_playlist', methods=['POST'])
def add_to_playlist():
    song = request.json['song']
    user = session['user']

    db = get_db()
    cur = db.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS playlist (
            username TEXT,
            song TEXT
        )
    """)

    cur.execute(
        "INSERT INTO playlist VALUES (?, ?)",
        (user, song)
    )

    db.commit()
    db.close()

    return jsonify({"status": "saved"})


@app.route('/remove_from_playlist', methods=['POST'])
def remove_from_playlist():
    song = request.json['song']
    user = session['user']

    db = get_db()
    cur = db.cursor()

    cur.execute(
        "DELETE FROM playlist WHERE username=? AND song=?",
        (user, song)
    )

    db.commit()
    db.close()

    return jsonify({"status": "removed"})


# ---------- RECENTLY PLAYED ----------
@app.route('/add_recent', methods=['POST'])
def add_recent():
    song = request.json['song']
    user = session['user']

    db = get_db()
    cur = db.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS recently_played (
            username TEXT,
            song TEXT,
            played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute(
        "INSERT INTO recently_played (username, song) VALUES (?, ?)",
        (user, song)
    )

    # Keep only last 5
    cur.execute("""
        DELETE FROM recently_played
        WHERE username=?
        AND rowid NOT IN (
            SELECT rowid FROM recently_played
            WHERE username=?
            ORDER BY played_at DESC
            LIMIT 5
        )
    """, (user, user))

    db.commit()
    db.close()

    return jsonify({"status": "saved"})


# ---------- MUSIC STREAM ----------
@app.route('/music/<path:filename>')
def music(filename):
    return send_from_directory(SONGS_FOLDER, filename)


# ---------- RUN ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

