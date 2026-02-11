from flask import Flask, render_template, request, redirect, session, url_for, flash, send_from_directory
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "secretkey123"

DB_PATH = "kairanban.db"
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =========================
# DB初期化
# =========================
def init_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row

    db.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            filename TEXT,
            category TEXT NOT NULL,
            likes INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    admin = db.execute("SELECT * FROM users WHERE username='admin'").fetchone()
    user1 = db.execute("SELECT * FROM users WHERE username='user1'").fetchone()

    if not admin:
        db.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                   ("admin", "pass123", "admin"))
    if not user1:
        db.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                   ("user1", "userpass", "user"))

    db.commit()
    db.close()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


init_db()

# =========================
# 閲覧ページ
# =========================
@app.route("/")
def index():
    if "username" not in session:
        return redirect(url_for("login"))

    category = request.args.get("category", "イベント")

    db = get_db()
    posts = db.execute(
        "SELECT * FROM posts WHERE category=? ORDER BY created_at DESC",
        (category,)
    ).fetchall()
    db.close()

    return render_template(
        "index.html",
        posts=posts,
        current_category=category,
        role=session["role"]
    )

# =========================
# 投稿画面表示（追加）
# =========================
@app.route("/create", methods=["GET"])
def create_page():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("create.html")

# =========================
# 投稿処理
# =========================
@app.route("/create", methods=["POST"])
def create():
    if "username" not in session:
        return redirect(url_for("login"))

    title = request.form["title"]
    content = request.form["content"]
    category = request.form["category"]
    file = request.files.get("file")
    filename = None

    if file and file.filename != "":
        filename = file.filename
        file.save(os.path.join(UPLOAD_FOLDER, filename))

    db = get_db()
    db.execute("""
        INSERT INTO posts (title, content, filename, category)
        VALUES (?, ?, ?, ?)
    """, (title, content, filename, category))
    db.commit()
    db.close()

    return redirect(url_for("index", category=category))

# =========================
# いいね機能
# =========================
@app.route("/like/<int:post_id>")
def like(post_id):
    if "username" not in session:
        return redirect(url_for("login"))

    db = get_db()
    db.execute("UPDATE posts SET likes = likes + 1 WHERE id=?", (post_id,))
    db.commit()
    db.close()

    return redirect(request.referrer or url_for("index"))


# =========================
# 編集
# =========================
@app.route("/edit/<int:post_id>", methods=["GET", "POST"])
def edit(post_id):
    if "username" not in session:
        return redirect(url_for("login"))

    db = get_db()

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        category = request.form["category"]

        db.execute("""
            UPDATE posts
            SET title=?, content=?, category=?
            WHERE id=?
        """, (title, content, category, post_id))

        db.commit()
        db.close()

        return redirect(url_for("index", category=category))

    post = db.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()
    db.close()

    return render_template("edit.html", post=post)

# =========================
# 削除
# =========================
@app.route("/delete/<int:post_id>")
def delete(post_id):
    if "username" not in session or session["role"] != "admin":
        flash("権限がありません")
        return redirect(url_for("index"))

    db = get_db()
    db.execute("DELETE FROM posts WHERE id=?", (post_id,))
    db.commit()
    db.close()

    return redirect(url_for("index"))

# =========================
# ログイン
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        ).fetchone()
        db.close()

        if user:
            session["username"] = user["username"]
            session["role"] = user["role"]
            return redirect(url_for("index"))
        else:
            flash("ユーザー名かパスワードが違います")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# =========================
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# =========================
if __name__ == "__main__":
    app.run(debug=True)

