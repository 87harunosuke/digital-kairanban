import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)

# ===== 設定 =====
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///posts.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = "static/uploads"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 最大16MB

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}

db = SQLAlchemy(app)

# ===== データベースモデル =====
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(300), nullable=True)
    filename = db.Column(db.String(300), nullable=True)
    filetype = db.Column(db.String(10), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ===== ファイル形式チェック =====
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ===== ホーム画面 =====
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        content = request.form.get("content")
        file = request.files.get("file")

        filename = None
        filetype = None

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)
            filetype = filename.rsplit(".", 1)[1].lower()

        new_post = Post(content=content, filename=filename, filetype=filetype)
        db.session.add(new_post)
        db.session.commit()

        return redirect(url_for("home"))

    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template("index.html", posts=posts)

# ===== 削除機能 =====
@app.route("/delete/<int:id>")
def delete(id):
    post = Post.query.get_or_404(id)

    if post.filename:
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], post.filename)
        if os.path.exists(filepath):
            os.remove(filepath)

    db.session.delete(post)
    db.session.commit()
    return redirect(url_for("home"))

if __name__ == "__main__":
    os.makedirs("static/uploads", exist_ok=True)
    with app.app_context():
        db.create_all()
    app.run(debug=True)
