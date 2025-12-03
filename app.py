import os
from datetime import datetime

import requests
from dotenv import load_dotenv
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
)
from werkzeug.security import check_password_hash

from dao.products_dao import ProductDAO
from dao.users_dao import UserDAO, UserAlreadyExists
from db import get_connection  # ← 自作の db.py から接続関数をインポート

# ------------------------------
# 初期化
# ------------------------------
load_dotenv()  # .env 読み込み
GOOGLE_PLACES_KEY = os.getenv("GOOGLE_PLACES_KEY")

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-me"  # 本番は環境変数へ

# --- テスト用ユーザ（DBなしで動かしたいとき用・不要なら消してOK） ---
users = {
    "test@example.com": {"password": "pass"},
    "test": {"password": "pass"},
}


# ------------------------------
# ヘルパ
# ------------------------------
def _parse_dt(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return datetime.min


def is_logged_in() -> bool:
    return "user" in session


# ------------------------------
# ルート
# ------------------------------
@app.route("/")
def home():
    return render_template(
        "index.html",
        logged_in=is_logged_in(),
        user=session.get("user"),
    )


# --- ログイン ---
@app.route("/login", methods=["GET", "POST"])
def login():
    # すでにログイン済みならホームへ
    if is_logged_in():
        return redirect(url_for("home"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""

        user = UserDAO.find_by_email(email)

        # ★ DAO 側のプロパティ名に合わせて id / user_id を調整してね
        if user and check_password_hash(user.password_hash, password):
            session["user"] = email
            session["user_id"] = getattr(user, "id", getattr(user, "user_id", None))
            if session["user_id"] is None:
                # 念のためフォールバック（なければログインさせない）
                flash("ユーザーIDが取得できませんでした。", "danger")
                return redirect(url_for("login"))
            return redirect(url_for("home"))

        # テスト用ユーザ（必要なければ消してOK）
        if email in users and users[email]["password"] == password:
            session["user"] = email
            session["user_id"] = 0  # ダミー
            return redirect(url_for("home"))

        flash("メールアドレスまたはパスワードが正しくありません。", "danger")
        return redirect(url_for("login"))

    return render_template("login.html")


# --- ログアウト ---
@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("user_id", None)
    # 成功メッセージはいらないと言っていたので flash は出さない
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


# ------------------------------
# 商品検索まわり
# ------------------------------
def search_products_service(
    q: str | None,
    sort: str | None,
    price_min: int | None,
    price_max: int | None,
):
    """
    ProductDAO を呼び出して検索結果一覧をつくるサービス関数
    """
    q = (q or "").strip()
    sort = (sort or "price_asc").strip()

    if q:
        products = ProductDAO.search_by_keyword(q)
    else:
        products = []

    # ソート（DB側に任せているならここは簡易）
    if sort == "price_asc":
        products.sort(key=lambda p: getattr(p, "price", 0))
    elif sort == "recent":
        products.sort(
            key=lambda p: _parse_dt(getattr(p, "updated_at", "1970-01-01T00:00:00")),
            reverse=True,
        )
    elif sort == "trust_desc":
        products.sort(key=lambda p: getattr(p, "trust", 0), reverse=True)

    # 価格フィルタ（必要なら）
    if price_min is not None:
        products = [p for p in products if getattr(p, "price", 0) >= price_min]
    if price_max is not None:
        products = [p for p in products if getattr(p, "price", 0) <= price_max]

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

    # ★ ログイン中ユーザーの「買い物メモに入っている product_id 一覧」
    memo_product_ids = set()
    if is_logged_in():
        user_id = session.get("user_id")
        if user_id:

            # 🔽 ここが追加部分！
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT DATABASE(), COUNT(*) FROM shopping_memos")
                    dbname, cnt = cur.fetchone()
                    print("DEBUG search_products DB:", dbname, "rows:", cnt)

            # 🔽 ここから元の処理
            sql = "SELECT product_id FROM shopping_memos WHERE user_id = %s"
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (user_id,))
                    for (pid,) in cur.fetchall():
                        memo_product_ids.add(pid)

    print("DEBUG memo_product_ids:", memo_product_ids)

    store_names: list[str] = []  # 将来のフィルタ用

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
        memo_product_ids=memo_product_ids,
    )


# --- 買い物メモ 追加・削除 ---
@app.route("/memo/add", methods=["POST"])
def add_to_memo():
    # 未ログインならログインへ
    if not is_logged_in():
        flash("買い物メモを使うにはログインしてください。", "warning")
        return redirect(url_for("login"))

    action = request.form.get("action")  # "add" or "remove"
    product_id_raw = request.form.get("product_id")

    try:
        product_id = int(product_id_raw)
    except (TypeError, ValueError):
        print("DEBUG /memo/add: invalid product_id_raw =", product_id_raw)
        flash("不正な商品です。", "danger")
        return redirect(request.referrer or url_for("search_products"))

    user_id = session.get("user_id")
    if user_id is None:
        print("DEBUG /memo/add: session user_id is None")
        flash("ユーザー情報が取得できませんでした。", "danger")
        return redirect(url_for("login"))

    print("DEBUG /memo/add START:",
          "action=", action, "user_id=", user_id, "product_id=", product_id)

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
        print("DEBUG /memo/add: unknown action =", action)
        flash("不正な操作です。", "danger")
        return redirect(request.referrer or url_for("search_products"))

    try:
        with get_connection() as conn:
            # どのDBにつながっているか確認
            with conn.cursor() as cur:
                cur.execute("SELECT DATABASE()")
                (dbname,) = cur.fetchone()
                print("DEBUG /memo/add: DATABASE() =", dbname)

            with conn.cursor() as cur:
                cur.execute(sql, (user_id, product_id))
                print("DEBUG /memo/add: executed SQL, rowcount =", cur.rowcount)

            conn.commit()
            print("DEBUG /memo/add: COMMIT OK")

    except Exception as e:
        print("ERROR /memo/add: DB error:", repr(e))
        flash("データベース処理でエラーが発生しました。", "danger")
        return redirect(request.referrer or url_for("search_products"))

    flash(msg, "success")
    return redirect(request.referrer or url_for("search_products"))



# ------------------------------
# Google Places API（近隣店舗検索）
# ------------------------------
@app.route("/api/nearby_stores", methods=["POST"])
def api_nearby_stores():
    data = request.get_json() or {}
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
        "includedTypes": ["supermarket"],
        "maxResultCount": 20,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": 1500,
            }
        },
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
        places.append(
            {
                "name": p.get("displayName", {}).get("text"),
                "address": p.get("formattedAddress"),
                "lat": loc.get("latitude"),
                "lng": loc.get("longitude"),
                "rating": p.get("rating"),
            }
        )

    return jsonify({"places": places})


# --- 近隣店舗画面 ---
@app.route("/search/stores")
def search_stores():
    return render_template(
        "search_stores.html",
        logged_in=is_logged_in(),
        user=session.get("user"),
    )


# ------------------------------
# プレースホルダー画面
# ------------------------------
@app.route("/favorites/stores")
def favorites_stores():
    return _placeholder("お気に入り店舗画面")


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

