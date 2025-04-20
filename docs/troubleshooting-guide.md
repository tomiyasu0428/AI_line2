# トラブルシューティングガイド

このガイドでは、AI予定管理秘書アプリの開発中に発生した主な問題とその解決策をまとめています。

## LINE Webhook関連の問題

### 問題: Webhook 404 Not Found エラー

**エラーメッセージ**:
```
Error
The webhook returned an HTTP status code other than 200.(404 Not Found)

Confirm that your bot server returns status code 200 in response to the HTTP POST request sent from the LINE Platform.
```

**原因**:
1. ngrokのURLが変更されたが、LINE DevelopersコンソールのWebhook URLが更新されていなかった
2. 環境変数の`APP_BASE_URL`が正確なngrokのURLと一致していなかった
3. ngrokのURLが不完全だった（ドメイン部分が途中で切れていた）

**解決策**:
1. `curl http://localhost:4040/api/tunnels`コマンドで最新のngrokのURLを確認
2. 環境変数の`APP_BASE_URL`を正確なngrokのURLに更新
3. LINE DevelopersコンソールのWebhook URLを更新（`https://<ngrok-url>/line/callback`）
4. アプリケーションを再起動して変更を反映

**検証方法**:
```bash
curl -X POST http://localhost:8080/line/callback
```
正常な場合は`{"detail":"Invalid signature"}`というレスポンスが返ります。これはLINE Platformからのリクエストには署名が含まれており、その署名が検証できない場合に返されるエラーです。

## Google OAuth認証関連の問題

### 問題: リダイレクトURI不一致エラー

**エラーメッセージ**:
```
redirect_uri_mismatch
```

**原因**:
1. Google Cloud Consoleで設定されたリダイレクトURIとアプリケーションのコードで使用されるリダイレクトURIが一致していなかった
2. ngrokのURLが変更されたが、Google Cloud Consoleの承認済みリダイレクトURIが更新されていなかった
3. リダイレクトURIのパスが不完全だった（`/oauth2callback`が`/oauth2call`になっていた）

**解決策**:
1. アプリケーションのコードを確認し、正確なリダイレクトURIを特定（`/google/oauth2callback`）
2. 環境変数の`APP_BASE_URL`を正確なngrokのURLに更新
3. Google Cloud Consoleで承認済みリダイレクトURIを更新（`https://<ngrok-url>/google/oauth2callback`）
4. アプリケーションを再起動して変更を反映

## ポート関連の問題

### 問題: ポート競合エラー

**エラーメッセージ**:
```
ERROR: [Errno 48] Address already in use
```

**原因**:
1. 以前のアプリケーションのインスタンスが終了せずに残っていた
2. 別のプロセスが同じポートを使用していた
3. 環境変数の`PORT`とコードで指定されたポートが異なっていた

**解決策**:
1. `lsof -i :<port>`コマンドで指定ポートを使用しているプロセスを確認
2. `kill -9 <PID>`コマンドでプロセスを終了
3. 環境変数の`PORT`とコードで指定されたポートを一致させる
4. 別のポートを使用するように設定を変更

## 環境変数関連の問題

### 問題: 環境変数の不一致

**原因**:
1. `.env`ファイルの変更が反映されていなかった
2. ngrokのURLが変更されたが、環境変数の`APP_BASE_URL`が更新されていなかった
3. アプリケーションの再起動が行われていなかった

**解決策**:
1. `.env`ファイルの内容を確認し、必要な変更を加える
2. 特に`APP_BASE_URL`が最新のngrokのURLと一致しているか確認
3. アプリケーションを再起動して変更を反映

## ベストプラクティス

1. **ngrokのURL管理**:
   - ngrokを起動するたびに新しいURLが生成されるため、毎回URLを確認し、関連する設定を更新する
   - `curl http://localhost:4040/api/tunnels`コマンドで最新のngrokのURLを確認できる

2. **環境変数の管理**:
   - 重要な設定は`.env`ファイルで一元管理する
   - 特に`APP_BASE_URL`は外部サービスとの連携に重要なので、常に最新のngrokのURLに更新する

3. **ポート管理**:
   - 環境変数の`PORT`とコードで指定されたポートを一致させる
   - ポート競合が発生した場合は、`lsof -i :<port>`と`kill -9 <PID>`コマンドを使用して解決する

4. **外部サービスの設定確認**:
   - LINE DevelopersコンソールとGoogle Cloud Consoleの設定を定期的に確認する
   - 特にWebhook URLとリダイレクトURIが最新のngrokのURLと一致しているか確認する

これらの問題と解決策を理解することで、AI予定管理秘書アプリの開発と運用がスムーズに行えるようになります。
