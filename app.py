from flask import Flask, render_template

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-me"  # 後でenv変数に退避推奨

# --- Home ---
@app.route("/")
def home():
    return render_template("index.html")

# --- プレースホルダー（未実装画面） ---
@app.route("/login")
def login():
    return _placeholder("ログイン画面")

@app.route("/register")
def register():
    return _placeholder("新規会員登録画面")

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
    # 追加のテンプレートは作らず、この場で簡易HTMLを返す
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
    # 開発用サーバ（本番ではWSGI/ASGIを使用）
    app.run(host="127.0.0.1", port=5000, debug=True)


    #おっぱいおっぱい
