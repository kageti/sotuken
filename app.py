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
from dao.favorite_dao import FavoriteDAO
from dao.favorite_stores_dao import FavoriteStoreDAO
from dao.store_dao import StoreDAO
from dao.product_prices_dao import ProductPricesDAO



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

@app.after_request
def add_no_cache_headers(response):
    # login画面だけはキャッシュ禁止（戻る対策）
    if request.path == "/login":
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


# ------------------------------
# ヘルパ
# ------------------------------
def _parse_dt(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return datetime.min


def is_logged_in() -> bool:
     # ログイン中かどうかは user_id の有無で判定する
    return "user_id" in session


@app.context_processor
def inject_user():
    """
    すべてのテンプレートから、共通で
      - logged_in
      - user
    が参照できるようにする。
    """
    return {
        "logged_in": is_logged_in(),
        "user": session.get("user"),
    }


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
    # ★ すでにログイン済みならログイン画面を表示しない
    if "user" in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""

        user = UserDAO.find_by_email(email)

        if user and check_password_hash(user.password_hash, password):
            session.clear()  # ★ 念のため一度クリア
            session["user"] = email
            session["user_id"] = user.id
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

# =========================
# 店舗サジェスト API（店舗名の候補を返す）
# =========================
@app.route("/api/store_suggest")
def api_store_suggest():
    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        # 1文字だけだと候補が多すぎるので返さない
        return jsonify({"stores": []})

    from difflib import SequenceMatcher

    # 1) DB から「名前 LIKE %q%」で候補を取る
    candidates = StoreDAO.search_by_name_like(q, limit=30)

    # 2) Python 側で簡易スコアリング（似ている順に並び替え）
    scored = []
    for s in candidates:
        score = SequenceMatcher(None, q, s.name).ratio()
        scored.append((score, s))

    scored.sort(key=lambda t: t[0], reverse=True)
    top = scored[:10]

    stores_json = [
        {
            "id": s.id,
            "name": s.name,
            "address": s.address or "",
        }
        for score, s in top
    ]

    return jsonify({"stores": stores_json})


# --- 買い物メモ 追加・削除 ---
@app.route("/memo/add", methods=["POST"])
def add_to_memo():
    # 未ログインならログインへ
    if not is_logged_in():
        flash("買い物メモを使うにはログインしてください。", "warning")
        return redirect(url_for("login"))

    action = request.form.get("action")  # "add" or "remove"
    product_id_raw = request.form.get("product_id")
    store_key = request.form.get("store_key")
    store_name = request.form.get("store_name")

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
@app.route("/api/nearby_stores", methods=["POST"])
def api_nearby_stores():
    data = request.get_json() or {}
    lat = data.get("lat")
    lng = data.get("lng")

    if lat is None or lng is None:
        return jsonify({"error": "lat, lng が必要です"}), 400

    if not GOOGLE_PLACES_KEY:
        return jsonify({
            "error": "GOOGLE_PLACES_KEY が設定されていません。.env を確認してください。"
        }), 500

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
                "radius": 1500,  # m
            }
        },
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        # ここでエラー内容をそのまま返す（フロントで表示できる）
        return jsonify({"error": f"Places API error: {e}"}), 500

    raw = resp.json()
    places = []

    for p in raw.get("places", []):
        loc = p.get("location", {})
        places.append({
            "id": p.get("id"),
            "name": p.get("displayName", {}).get("text"),
            "address": p.get("formattedAddress"),
            "lat": loc.get("latitude"),
            "lng": loc.get("longitude"),
            "rating": p.get("rating"),
        })

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


@app.route("/favorites")
def favorite_products():
    if not is_logged_in():
        flash("ログインしてください", "warning")
        return redirect(url_for("login"))

    user_id = session.get("user_id")

    favorites = FavoriteDAO.list_favorites_by_user(user_id)

    return render_template(
        "favorite_products.html",
        favorites=favorites,
    )
    return render_template("favorite_products.html", favorites=favorites)




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

    user_id = session.get("user_id")
    if user_id is None:
        flash("ユーザー情報が取得できませんでした。", "danger")
        return redirect(url_for("login"))

    # --- GET: フォーム + 履歴表示 ---
    if request.method == "GET":
        prefill_store_name = request.args.get("store_name", "") or ""
        recent_posts = ProductPricesDAO.list_recent(limit=10)

        return render_template(
            "price_post.html",
            logged_in=is_logged_in(),
            user=session.get("user"),
            store_name=prefill_store_name,
            recent_posts=recent_posts,
        )

    # --- POST: DBに保存 ---
    jan = (request.form.get("jan") or "").strip()
    store_name = (request.form.get("store_name") or "").strip()
    store_id_raw = (request.form.get("store_id") or "").strip()
    price_str = (request.form.get("price") or "").strip()

    # JAN必須
    if not jan:
        flash("JANコードは必須です。", "warning")
        return redirect(url_for("price_post"))
    if not jan.isdigit():
        flash("JANコードは数字のみで入力してください。", "warning")
        return redirect(url_for("price_post"))

    if not store_name:
        flash("店舗名を入力してください。", "warning")
        return redirect(url_for("price_post"))

    if not price_str.isdigit():
        flash("価格は整数で入力してください。", "warning")
        return redirect(url_for("price_post"))
    price = int(price_str)

    store_id = None
    if store_id_raw.isdigit():
        store_id = int(store_id_raw)

    # 商品マスタからJANで商品を一意特定
    product = ProductDAO.find_by_jan(jan)
    if not product:
        flash("このJANコードの商品が商品マスタにありません。先に商品マスタへ登録してください。", "danger")
        return redirect(url_for("price_post"))

    product_id = getattr(product, "id", None)
    product_name = getattr(product, "name", "(名称未設定)")

    # ★DBへ保存（これでページ遷移しても消えない）
    ProductPricesDAO.insert(
        user_id=user_id,
        store_id=store_id,
        store_name=store_name,
        jan=jan,
        product_id=product_id,
        product_name=product_name,
        price=price,
    )

    flash(f"『{product_name}』の価格を投稿しました。", "success")
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

