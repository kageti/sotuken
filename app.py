import os
import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime
from dao.products_dao import ProductDAO
from dao.users_dao import UserDAO, UserAlreadyExists
from werkzeug.security import check_password_hash
import os
import requests
from dotenv import load_dotenv

load_dotenv()  # .env 読み込み
GOOGLE_PLACES_KEY = os.getenv("GOOGLE_PLACES_KEY")

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-me"  # 本番は環境変数へ

# --- 仮ユーザーストア（DBなしで動かす用） ---
users = {
    "test": {"password": "pass"},
    "test@example.com": {"password": "pass"},
}


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

# --- 買い物メモに追加 ---
@app.post("/memo/add")
def add_to_memo():
    # セッションに memo がなければ作る
    if "memo" not in session:
        session["memo"] = []

    product_id = request.form.get("product_id")
    if product_id and product_id not in session["memo"]:
        session["memo"].append(product_id)
        session.modified = True
        flash("買い物メモに追加しました。", "success")

    # 元のページ（検索結果）に戻る
    return redirect(request.referrer or url_for("search_products")) 

# --- 近隣店舗などプレースホルダー ---
@app.route("/favorites/stores")
def favorites_stores():
    return _placeholder("お気に入り店舗画面")

# =========================
# Google Places API（近隣店舗検索）
# =========================
@app.route("/api/nearby_stores", methods=["POST"])
def api_nearby_stores():
    data = request.get_json()
    lat = data.get("lat")
    lng = data.get("lng")

    if lat is None or lng is None:
        return jsonify({"error": "lat, lng が必要です"}), 400

    url = "https://places.googleapis.com/v1/places:searchNearby"

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_PLACES_KEY,
        "X-Goog-FieldMask": (
            "places.displayName,places.formattedAddress,"
            "places.location,places.rating"
        ),
    }

    payload = {
        # スーパーだけに絞る（必要に応じて追加）
        "includedTypes": ["supermarket"],
        "maxResultCount": 20,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": 1500  # 半径 1.5km
            }
        }
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        return jsonify({"error": f"Places API error: {e}"}), 500

    raw = resp.json()
    places = []

    for p in raw.get("places", []):
        loc = p.get("location", {})
        places.append({
            "name": p.get("displayName", {}).get("text"),
            "address": p.get("formattedAddress"),
            "lat": loc.get("latitude"),
            "lng": loc.get("longitude"),
            "rating": p.get("rating")
        })

    return jsonify({"places": places})


# --- 近隣店舗検索　---
@app.route("/search/stores")
def search_stores():
    return render_template(
        "search_stores.html",
        logged_in=is_logged_in(),
        user=session.get("user")
    )


@app.route("/purchases")
def purchases():
    return _placeholder("購入履歴画面")

@app.route("/cart")
def cart():
    return _placeholder("買い物メモ画面")

@app.route("/price/post")
def price_post():
    return _placeholder("価格情報提供（投稿）画面")

@app.route("/mypage")
def mypage():
    return _placeholder("mypage.html")

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
