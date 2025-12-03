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
from dao.shopping_memo_dao import ShoppingMemoDAO
from db import get_connection
from flask import get_flashed_messages



load_dotenv()  # .env 読み込み
GOOGLE_PLACES_KEY = os.getenv("GOOGLE_PLACES_KEY")

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-me"  # 本番は環境変数へ

# --- 仮ユーザーストア（DBなしで動かす用） ---
users = {
    "test": {"password": "pass"},
    "test@example.com": {"password": "pass"},
}

# --- 仮 価格投稿ストア（DBなしで動かす用） ---
MOCK_PRICE_POSTS = []  # 将来は DB（product_prices テーブル）に差し替え予定


def add_mock_price_post(jan, product_name, store_name, price, user_email):
    """
    将来的に DAO を呼ぶ形に差し替えるためのラッパ関数。
    今はメモリ上のリストに追加するだけ。
    """
    post = {
        "id": len(MOCK_PRICE_POSTS) + 1,
        "jan": jan,
        "product_name": product_name,
        "store_name": store_name,
        "price": price,
        "user_email": user_email,
        "posted_at": datetime.now().isoformat(timespec="seconds"),
    }
    MOCK_PRICE_POSTS.append(post)
    return post["id"]

# ユーティリティ：日付→datetime
def _parse_dt(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return datetime.min

# --- 認証ヘルパ ---
def is_logged_in():
    return "user_id" in session

# --- Home ---
@app.route("/")
def home():
    return render_template("index.html", logged_in=is_logged_in(), user=session.get("user"))

# --- ログイン ---
@app.route("/login", methods=["GET", "POST"])
def login():
    # ★ ログイン画面に来た時点でフラッシュ全部破棄
    get_flashed_messages()

    # ★ すでにログイン済みならホームへ追い返す
    if is_logged_in():
        return redirect(url_for("home"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""
        user = UserDAO.find_by_email(email)

        if user and check_password_hash(user.password_hash, password):
            session["user"] = email
            session["user_id"] = user.id
            # ★ ログイン成功時もメッセージ出さない
            return redirect(url_for("home"))

        # ★ このメッセージだけ残す（間違えたとき）
        flash("メールアドレスまたはパスワードが正しくありません。", "danger")
        return redirect(url_for("login"))

    return render_template("login.html")


# --- ログアウト ---
@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("user_id", None)  #  追加
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

 # ★ ここから追加：ログイン中ユーザーの「メモ済み product_id 一覧」を取る
    memo_product_ids = set()
    if is_logged_in():
        user_id = session.get("user")
        if user_id:
            sql = "SELECT product_id FROM shopping_memos WHERE user_id = %s"
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (user_id,))
                    for (pid,) in cur.fetchall():
                        memo_product_ids.add(pid)

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
        user=session.get("user"),
        memo_product_ids=memo_product_ids,  # ★ これをテンプレに渡す
    )

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

# --- 買い物メモ（追加 or 削除） ---
@app.route("/memo/add", methods=["POST"])
def add_to_memo():
    # 未ログインなら静かにログインへ
    if not is_logged_in():
        return redirect(url_for("login"))

    # ラジオボタンの値: "add" or "remove"
    action = request.form.get("action")
    product_id_raw = request.form.get("product_id")

    try:
        product_id = int(product_id_raw)
    except (TypeError, ValueError):
        flash("不正な商品です。", "danger")
        return redirect(request.referrer or url_for("search_products"))

    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    # --- DB処理 ---
    if action == "add":
        sql = """
            INSERT IGNORE INTO shopping_memos (user_id, product_id)
            VALUES (%s, %s)
        """
        msg = "買い物メモに追加しました。"
    elif action == "remove":
        sql = """
            DELETE FROM shopping_memos
            WHERE user_id = %s AND product_id = %s
        """
        msg = "買い物メモから削除しました。"
    else:
        flash("不正な操作です。", "danger")
        return redirect(request.referrer or url_for("search_products"))

    from db import get_connection
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id, product_id))
        conn.commit()

    flash(msg, "success")
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
    data = request.get_json() or {}
    lat = data.get("lat")
    lng = data.get("lng")

    if lat is None or lng is None:
        return jsonify({"error": "lat, lng が必要です"}), 400

    if not GOOGLE_PLACES_KEY:
        return jsonify({"error": "GOOGLE_PLACES_KEY が設定されていません。.env を確認してください。"}), 500

    url = "https://places.googleapis.com/v1/places:searchNearby"

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_PLACES_KEY,
        "X-Goog-FieldMask": (
            "places.id,places.displayName,places.formattedAddress,"
            "places.location,places.rating"
        ),
    }

    payload = {
        "includedTypes": ["supermarket"],  # スーパーに絞る
        "maxResultCount": 20,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": 1500,
            }
        },
    }

    # ★ ここから下がさっきの try ブロック
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
            "place_id": p.get("id"),
            "name": p.get("displayName", {}).get("text"),
            "address": p.get("formattedAddress"),
            "lat": loc.get("latitude"),
            "lng": loc.get("longitude"),
            "rating": p.get("rating"),
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

# =========================
# 商品価格投稿画面（JAN必須＋DBから商品名取得）
# =========================
@app.route("/price/post", methods=["GET", "POST"])
def price_post():
    if not is_logged_in():
        flash("価格を投稿するにはログインが必要です。", "warning")
        return redirect(url_for("login"))

    # --- GET: フォーム表示 ---
    if request.method == "GET":
        prefill_store_name = request.args.get("store_name", "") or ""
        return render_template(
            "price_post.html",
            logged_in=is_logged_in(),
            user=session.get("user"),
            store_name=prefill_store_name,
            recent_posts=MOCK_PRICE_POSTS[-5:],  # 直近5件だけ表示
        )

    # --- POST: 入力内容を検証して、メモリ上に保存 ---
    jan = (request.form.get("jan") or "").strip()
    store_name = (request.form.get("store_name") or "").strip()
    price_str = (request.form.get("price") or "").strip()

    # ✅ JANコード必須
    if not jan:
        flash("JANコードは必須です。入力してください。", "warning")
        return redirect(url_for("price_post"))

    # ✅ JANコードは数字のみ（必要なら桁数チェックも追加可）
    if not jan.isdigit():
        flash("JANコードは数字のみで入力してください。", "warning")
        return redirect(url_for("price_post"))

    # ✅ 店舗名必須
    if not store_name:
        flash("店舗名を入力してください。", "warning")
        return redirect(url_for("price_post"))

    # ✅ 価格チェック
    if not price_str.isdigit():
        flash("価格は整数で入力してください。", "warning")
        return redirect(url_for("price_post"))
    price = int(price_str)

    # --- DBから商品名などを取得 ---
    # ここでは ProductDAO に find_by_jan(jan) がある前提
    product = None
    try:
        # もしまだメソッドが無い場合は、この一行で AttributeError が出るので、
        # 後ろに書いてある「暫定実装」を使ってください。
        product = ProductDAO.find_by_jan(jan)
    except AttributeError:
        # ★ 暫定版：search_by_keyword で JAN を検索して最初の1件を採用
        candidates = ProductDAO.search_by_keyword(jan)
        if candidates:
            product = candidates[0]

    if not product:
        flash("このJANコードの商品が商品マスタに登録されていません。先に商品登録を行ってください。", "danger")
        return redirect(url_for("price_post"))

    # Product オブジェクトから商品名を取得（name という属性名を想定）
    product_name = getattr(product, "name", None) or "(名称未設定)"

    user_email = session.get("user")

    # 将来 DB に差し替える箇所（今はメモリに保存）
    add_mock_price_post(
        jan=jan,
        product_name=product_name,
        store_name=store_name,
        price=price,
        user_email=user_email,
    )

    flash(f"『{product_name}』の価格情報を投稿しました。（現在はアプリ内の一時保存です）", "success")
    return redirect(url_for("price_post"))


@app.route("/mypage")
def mypage():
    if not is_logged_in():
        return redirect(url_for("login"))

    return render_template(
        "mypage.html",
        user=session.get("user"),
        logged_in=True,
        user_rating=4.2  # ← DB接続前の仮データ
    )


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
