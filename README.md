# -
買い物アプリ

開発時アプリの起動やエラーの確認、デバッグにターミナルを使用する。ターミナルはVScode最上部の左から７番目の項目をクリックして新しいターミナルから起動する。

======仮想環境======
仮想環境は各自のPCで実装する必要がある
1. venvファイルを作成する
python -m venv venv
2. 仮想環境を有効化する
venv\Scripts\activate


----エラーが発生した場合----
1. PCの設定がデフォルトの場合スクリプトを実行できないためPowerShellを管理者として実行後下記のコマンドを実行
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
（その後YesかNoを聞かれた場合[Y]を入力）

3. 仮想環境が有効化された後にFlaskをインストール
pip install flask

4.　アプリを起動
python app.py

5.　アプリを終了
Ctrl + C


仮想環境を抜けたい場合
deactivate
をターミナルで実行


======仮IDとパスワード======
ID:test
password:pass