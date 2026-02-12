from flask import Flask, render_template, request, redirect, session, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "devkey")

# =========================
# Database設定（Render対応）
# =========================
database_url = os.environ.get("DATABASE_URL")

if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =========================
# モデル定義
# =========================
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    filename = db.Column(db.String(200))
    category = db.Column(db.String(50), nullable=False)
    likes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)

# =========================
# 初期化
# =========================
with app.app_context():
    db.create_all()

    if not User.query.filter_by(username="admin").first():
        db.session.add(User(username="admin", password="pass123", role="admin"))

    if not User.query.filter_by(username="user1").first():
        db.session.add(User(username="user1", password="userpass", role="user"))

    db.session.commit()

# =========================
# 閲覧ページ
# =========================
@app.route("/")
def index():
    if "username" not in session:
        return redirect(url_for("login"))

    category = request.args.get("category", "イベント")

    posts = Post.query.filter_by(category=category)\
        .order_by(Post.created_at.desc()).all()

    return render_template(
        "index.html",
        posts=posts,
        current_category=category
    )

# =========================
# 投稿画面
# =========================
@app.route("/create", methods=["GET", "POST"])
def create():
    if "username" not in session:
        return redirect(url_for("login"))

    # ★追加（投稿は管理者のみ）
    if session.get("role") != "admin":
        flash("投稿は管理者のみ可能です")
        return redirect(url_for("index"))

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        category = request.form["category"]
        file = request.files.get("file")
        filename = None

        if file and file.filename != "":
            filename = file.filename
            file.save(os.path.join(UPLOAD_FOLDER, filename))

        new_post = Post(
            title=title,
            content=content,
            filename=filename,
            category=category
        )

        db.session.add(new_post)
        db.session.commit()

        return redirect(url_for("index", category=category))

    return render_template("create.html")

# =========================
# いいね
# =========================
@app.route("/like/<int:post_id>")
def like(post_id):
    if "username" not in session:
        return redirect(url_for("login"))

    post = Post.query.get_or_404(post_id)
    post.likes += 1
    db.session.commit()

    return redirect(request.referrer or url_for("index"))

# =========================
# 編集
# =========================
@app.route("/edit/<int:post_id>", methods=["GET", "POST"])
def edit(post_id):
    if "username" not in session:
        return redirect(url_for("login"))

    # ★追加
    if session.get("role") != "admin":
        flash("編集は管理者のみ可能です")
        return redirect(url_for("index"))

    post = Post.query.get_or_404(post_id)

    if request.method == "POST":
        post.title = request.form["title"]
        post.content = request.form["content"]
        post.category = request.form["category"]
        db.session.commit()

        return redirect(url_for("index", category=post.category))

    return render_template("edit.html", post=post)


# =========================
# 削除
# =========================
@app.route("/delete/<int:post_id>")
def delete(post_id):
    if "username" not in session or session.get("role") != "admin":
        flash("権限がありません")
        return redirect(url_for("index"))

    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()

    return redirect(url_for("index"))

# =========================
# ログイン
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username, password=password).first()

        if user:
            session["username"] = user.username
            session["role"] = user.role
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

