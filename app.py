import os
import math
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
from dao.favorite_stores_dao import FavoriteStoreDAO
from dao.favorite_dao import FavoriteDAO

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
    favorite_product_ids = set()

    if is_logged_in():
        user_id = session.get("user_id")

        if user_id:
            # ① 買い物メモに入っている product_id を集める（今までの処理）
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT product_id FROM shopping_memos WHERE user_id = %s",
                        (user_id,)
                    )
                    for (pid,) in cur.fetchall():
                        memo_product_ids.add(pid)

            # ② お気に入りに登録している product_id を集める（新規）
            favorite_product_ids = FavoriteDAO.get_favorite_ids(user_id)

    # ③ 各商品にフラグを立てる
    for p in results:
        p.in_memo = (p.id in memo_product_ids)
        p.favorited = (p.id in favorite_product_ids)

    return render_template(
        "search_products.html",
        q=q,
        sort=sort,
        price_min=price_min,
        price_max=price_max,
        results=results,
        memo_product_ids=memo_product_ids,
        # favorite_product_ids を渡さなくても、p.favorited を使っているのでOK
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
        print("買い物メモに追加しました。")
    elif action == "remove":
        sql = """
            DELETE FROM shopping_memos
            WHERE user_id = %s AND product_id = %s
        """
        print("買い物メモから削除しました。")
    else:
        print("DEBUG /memo/add: unknown action =", action)
        flash("不正な操作です。", "danger")
        return redirect(request.referrer or url_for("search_products"))

    try:
        with get_connection() as conn:
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

    # ✅ 成功時はポップアップを出さず、静かに元の画面へ戻る
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
@app.route("/api/favorite_store", methods=["POST"])
def api_favorite_store():
    """近隣店舗画面から、お気に入り店舗を登録する API"""
    if "user_id" not in session:
        return jsonify({"ok": False, "error": "not_logged_in"}), 401

    data = request.get_json() or {}
    user_id = session["user_id"]

    store_id = data.get("store_id")
    store_name = data.get("store_name")
    latitude = data.get("lat")
    longitude = data.get("lng")
    open_now = data.get("open_now")  # 今回は None のままでOK

    if not store_id or not store_name:
        return jsonify({"ok": False, "error": "invalid_params"}), 400

    from dao.favorite_stores_dao import FavoriteStoreDAO

    FavoriteStoreDAO.add(
        user_id=user_id,
        store_id=store_id,
        store_name=store_name,
        latitude=latitude,
        longitude=longitude,
        open_now=open_now,
    )

    return jsonify({"ok": True})




# --- 近隣店舗画面 ---
@app.route("/search/stores")
def search_stores():
    return render_template(
        "search_stores.html",
        logged_in=is_logged_in(),
        user=session.get("user"),
    )

# ------------------------------
# お気に入り店舗画面
# ------------------------------
def calc_distance(lat1, lng1, lat2, lng2):
    """haversine formula（距離計算）"""
    R = 6371.0  # km
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

@app.route("/favorites/stores", methods=["GET", "POST"])
def favorites_stores():
    if not is_logged_in():
        flash("お気に入り店舗を利用するにはログインしてください。", "warning")
        return redirect(url_for("login"))

    user_id = session.get("user_id")
    if user_id is None:
        flash("ユーザー情報が取得できませんでした。", "danger")
        return redirect(url_for("login"))

    # --- 削除 POST 処理 ---
    if request.method == "POST":
        action = request.form.get("action")
        store_id = request.form.get("store_id")
        if action == "delete" and store_id:
            FavoriteStoreDAO.remove(user_id, store_id)
            flash("お気に入り店舗を削除しました。", "success")
        else:
            flash("不正な操作です。", "danger")
        return redirect(url_for("favorites_stores"))

    # --- GET: 一覧表示 ---
    sort = request.args.get("sort", "name")  # "name" or "distance"

    # 現在地（任意）: JS から lat/lng を付けて呼び出す想定
    lat_raw = request.args.get("lat")
    lng_raw = request.args.get("lng")
    try:
        user_lat = float(lat_raw) if lat_raw else None
        user_lng = float(lng_raw) if lng_raw else None
    except ValueError:
        user_lat = user_lng = None

    favorites = FavoriteStoreDAO.list_by_user(user_id)

    # 距離計算（位置情報が取れている場合のみ）
    for f in favorites:
        f.distance_km = None
        if (
            user_lat is not None
            and user_lng is not None
            and getattr(f, "latitude", None) is not None
            and getattr(f, "longitude", None) is not None
        ):
            f.distance_km = calc_distance(
                user_lat, user_lng, f.latitude, f.longitude
            )


    # 並び替え
    if sort == "distance":
        favorites.sort(key=lambda x: (x.distance_km is None, x.distance_km or 0.0))
    else:
        favorites.sort(key=lambda x: x.store_name or "")

    return render_template(
        "favorites_stores.html",
        favorites=favorites,
        sort=sort,
        user_lat=user_lat,
        user_lng=user_lng,
        logged_in=is_logged_in(),
        user=session.get("user"),
    )


# ------------------------------
# プレースホルダー画面
# ------------------------------
#@app.route("/favorites/stores")
#def favorites_stores():
#    return _placeholder("お気に入り店舗画面")


@app.route("/purchases")
def purchases():
    return _placeholder("購入履歴画面")


@app.route("/cart")
def cart():
    return _placeholder("買い物メモ画面")

# ------------------------------
# お気に入り商品 トグル（商品検索画面の★）
# ------------------------------
@app.route("/favorite/toggle", methods=["POST"])
def favorite_toggle():
    # ログインしていなければログイン画面へ
    if not is_logged_in():
        flash("お気に入り機能を使うにはログインしてください。", "warning")
        return redirect(url_for("login"))

    product_id_raw = request.form.get("product_id")
    try:
        product_id = int(product_id_raw)
    except (TypeError, ValueError):
        flash("不正な商品です。", "danger")
        return redirect(request.referrer or url_for("search_products"))

    user_id = session.get("user_id")
    if user_id is None:
        flash("ユーザー情報が取得できませんでした。", "danger")
        return redirect(url_for("login"))

    try:
        # dao.favorite_dao から import している FavoriteDAO をそのまま利用
        FavoriteDAO.toggle(user_id, product_id)
    except Exception as e:
        print("ERROR favorite_toggle:", repr(e))
        flash("お気に入り更新中にエラーが発生しました。", "danger")
        return redirect(request.referrer or url_for("search_products"))

    # ★ 成功したら元のページ（検索画面）に戻る
    return redirect(request.referrer or url_for("search_products"))


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

