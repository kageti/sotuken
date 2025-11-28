from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime
from dao.products_dao import ProductDAO
from dao.users_dao import UserDAO, UserAlreadyExists
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-me"  # 本番は環境変数へ

# --- 仮ユーザーストア（DBなしで動かす用） ---
users = {
    "test": {"password": "pass"},
    "test@example.com": {"password": "pass"},
}

# --- 仮プロダクトデータ（将来はDBに置換） ---
# 必要に応じて product_id を PK、JAN はユニークにする想定
""" MOCK_PRODUCTS = [
    {
        "product_id": 1,
        "jan": "4901234567890",
        "name": "明治 おいしい牛乳 1000ml",
        "brand": "明治",
        "category": "乳製品",
        "price": 228,
        "store": "スーパーA 広島駅前店",
        "trust": 72,
        "updated_at": "2025-11-05T10:12:00"
    },
    {
        "product_id": 2,
        "jan": "4902713123456",
        "name": "日清 カップヌードル しょうゆ 78g",
        "brand": "日清",
        "category": "インスタント",
        "price": 158,
        "store": "ドラッグB 猿猴橋店",
        "trust": 65,
        "updated_at": "2025-11-11T18:40:00"
    },
    {
        "product_id": 3,
        "jan": "4901777301234",
        "name": "コカ・コーラ 500ml ペット",
        "brand": "コカ・コーラ",
        "category": "飲料",
        "price": 98,
        "store": "スーパーA 広島駅前店",
        "trust": 80,
        "updated_at": "2025-11-06T12:00:00"
    },
    {
        "product_id": 4,
        "jan": "4901002134567",
        "name": "キッコーマン しょうゆ 1L",
        "brand": "キッコーマン",
        "category": "調味料",
        "price": 268,
        "store": "スーパーC 段原店",
        "trust": 55,
        "updated_at": "2025-11-10T09:25:00"
    },
    {
        "product_id": 5,
        "jan": "4901085198765",
        "name": "ハウス バーモントカレー 中辛 230g",
        "brand": "ハウス",
        "category": "レトルト",
        "price": 198,
        "store": "ドラッグB 猿猴橋店",
        "trust": 60,
        "updated_at": "2025-11-09T16:10:00"
    },
    {
        "product_id": 6,
        "jan": "4901411234001",
        "name": "サントリー 天然水 2L",
        "brand": "サントリー",
        "category": "飲料",
        "price": 95,
        "store": "スーパーD 横川店",
        "trust": 77,
        "updated_at": "2025-11-12T08:00:00"
    },
    {
        "product_id": 7,
        "jan": "4903301234567",
        "name": "ヤマザキ ダブルソフト 6枚",
        "brand": "山崎製パン",
        "category": "パン",
        "price": 178,
        "store": "スーパーC 段原店",
        "trust": 58,
        "updated_at": "2025-11-07T11:30:00"
    },
    {
        "product_id": 8,
        "jan": "4902720123012",
        "name": "UCC ブラック無糖 185g 缶",
        "brand": "UCC",
        "category": "飲料",
        "price": 78,
        "store": "コンビニE 広大病院前店",
        "trust": 68,
        "updated_at": "2025-11-08T21:05:00"
    },
] """

# ユーティリティ：日付→datetime
def _parse_dt(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return datetime.min

# --- 認証ヘルパ ---
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
        user = UserDAO.find_by_email(email)
        if user and check_password_hash(user.password_hash, password):
            session["user"] = email
            flash("ログインしました。", "success")
            return redirect(url_for("home"))
        if email in users and users[email]["password"] == password:
            session["user"] = email
            flash("ログインしました。", "success")
            return redirect(url_for("home"))
        flash("メールアドレスまたはパスワードが正しくありません。", "danger")
        return redirect(url_for("login"))
    return render_template("login.html")

# --- ログアウト ---
@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("ログアウトしました。", "info")
    return redirect(url_for("home"))

# --- 新規会員登録 ---
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm") or ""
        if not email or "@" not in email:
            flash("正しいメールアドレスを入力してください。", "warning")
            return redirect(url_for("register"))
        if len(password) < 6:
            flash("パスワードは6文字以上にしてください。", "warning")
            return redirect(url_for("register"))
        if password != confirm:
            flash("確認用パスワードが一致しません。", "warning")
            return redirect(url_for("register"))
        if UserDAO.find_by_email(email) or email in users:
            flash("このメールアドレスはすでに登録されています。", "danger")
            return redirect(url_for("register"))
        try:
            UserDAO.create_user(email, password)
        except UserAlreadyExists:
            flash("このメールアドレスはすでに登録されています。", "danger")
            return redirect(url_for("register"))
        flash("登録が完了しました。ログインしてください。", "success")
        return redirect(url_for("login"))
    return render_template("register.html")


# =========================
# 商品検索（仮データ版）
# =========================
def search_products_service(
    q: str | None,
    sort: str | None,
    price_min: int | None,
    price_max: int | None
):
    """
    DB（souken）の products テーブルから検索する想定。
    - q: フリーワード / JAN
    - sort: price_asc / recent / trust_desc （今はとりあえず名前順）
    - price_min/max: 価格フィルタ（あとで実装）
    """
    
    q = (q or "").strip()
    sort = (sort or "price_asc").strip()

    def match(product):
        # JAN 完全一致 or 前方一致
        if q and q.isdigit():
            if product["jan"].startswith(q):
                return True
        # テキスト部分一致（name, brand, category, store）
        if q:
            key = f"{product['name']} {product['brand']} {product['category']} {product['store']} {product['jan']}".lower()
            if q.lower() not in key:
                return False
        # 価格フィルタ
        if price_min is not None and product["price"] < price_min:
            return False
        if price_max is not None and product["price"] > price_max:
            return False
        return True

    if q:
        products = ProductDAO.search_by_keyword(q)
    else:
        products = []

    # まだ price, trust, updated_at などを DB 側で持っていない前提で、
    # いったんソートは「商品名」でごまかしておく
    if sort == "price_asc":
        products.sort(key=lambda p: getattr(p, "name", ""))
    elif sort == "recent":
        # updated_at カラムを Product に持たせたらここで使う
        products.sort(key=lambda p: getattr(p, "id", 0), reverse=True)
    elif sort == "trust_desc":
        # trust カラムを持たせたらここで使う
        products.sort(key=lambda p: getattr(p, "id", 0), reverse=True)

    # ひとまず price_min / price_max は未使用（あとで拡張）
    return products

@app.route("/search/products")
def search_products():
    q = request.args.get("q", "")
    sort = request.args.get("sort", "price_asc")
    price_min = request.args.get("price_min")
    price_max = request.args.get("price_max")

    try:
        price_min_i = int(price_min) if price_min else None
    except ValueError:
        price_min_i = None
    try:
        price_max_i = int(price_max) if price_max else None
    except ValueError:
        price_max_i = None

    results = search_products_service(q, sort, price_min_i, price_max_i)

    # ストア一覧（フィルタUIの将来拡張用）
    store_names = []

    return render_template(
        "search_products.html",
        q=q,
        sort=sort,
        price_min=price_min or "",
        price_max=price_max or "",
        results=results,
        store_names=store_names,
        logged_in=is_logged_in(),
        user=session.get("user")
    )

# --- 近隣店舗などプレースホルダー ---
@app.route("/favorites/stores")
def favorites_stores():
    return _placeholder("お気に入り店舗画面")

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
