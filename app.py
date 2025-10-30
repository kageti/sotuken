from flask import Flask, render_template, request, redirect, url_for, flash, session

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-me"  # 本番は環境変数へ

# --- 仮ユーザーストア（DBなしで動かす用） ---
# 既定で "test" / "test@example.com" のどちらでもログインOK、パスワードは "pass"
users = {
    "test": {"password": "pass"},
    "test@example.com": {"password": "pass"},
}

# --- ヘルパ ---
def is_logged_in():
    return "user" in session

# --- Home ---
@app.route("/")
def home():
    return render_template("index.html", logged_in=is_logged_in(), user=session.get("user"))

# --- ログイン ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""
        # 仮認証：メール欄に "test" または "test@example.com" かつ pw=="pass" でOK
        if email in users and users[email]["password"] == password:
            session["user"] = email
            flash("ログインしました。", "success")
            return redirect(url_for("home"))
        else:
            # まだDBがないため、未登録/パスワード不一致をまとめて「認証エラー」と表示
            flash("メールアドレスまたはパスワードが正しくありません。", "danger")
            return redirect(url_for("login"))
    # GET
    return render_template("login.html")

# --- ログアウト ---
@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("ログアウトしました。", "info")
    return redirect(url_for("home"))

# --- 新規会員登録（DBなしの簡易動作） ---
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm") or ""

        # 簡易バリデーション（最低限）
        if not email or "@" not in email:
            flash("正しいメールアドレスを入力してください。", "warning")
            return redirect(url_for("register"))
        if len(password) < 6:
            flash("パスワードは6文字以上にしてください。", "warning")
            return redirect(url_for("register"))
        if password != confirm:
            flash("確認用パスワードが一致しません。", "warning")
            return redirect(url_for("register"))
        if email in users:
            flash("このメールアドレスはすでに登録されています。", "danger")
            return redirect(url_for("register"))

        # 仮登録：メモリ上の dict に追加（サーバ再起動で消えます）
        users[email] = {"password": password}
        flash("登録が完了しました。ログインしてください。", "success")
        return redirect(url_for("login"))

    # GET
    return render_template("register.html")

# --- プレースホルダー（将来実装予定の画面用） ---
@app.route("/favorites/stores")
def favorites_stores():
    return _placeholder("お気に入り店舗画面")

@app.route("/search/products")
def search_products():
    return _placeholder("商品検索画面")

@app.route("/search/stores")
def search_stores():
    return _placeholder("近隣店舗検索画面")

@app.route("/purchases")
def purchases():
    return _placeholder("購入履歴画面")

@app.route("/cart")
def cart():
    return _placeholder("マイカート画面")

@app.route("/price/post")
def price_post():
    return _placeholder("価格情報提供（投稿）画面")

@app.route("/mypage")
def mypage():
    return _placeholder("マイページ画面")

def _placeholder(title: str) -> str:
    return f"""
    <!doctype html>
    <html lang="ja">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <title>{title} - 準備中</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-light">
        <div class="container py-5">
            <div class="card shadow-sm">
                <div class="card-body">
                    <h1 class="h4 mb-3">{title}</h1>
                    <p class="text-muted mb-4">このページは現在準備中です。実装が完了したら置き換えます。</p>
                    <a class="btn btn-primary" href="/">ホームに戻る</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
