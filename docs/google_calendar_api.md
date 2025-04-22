# Google Calendar API 機能一覧

Google Calendar APIは、Googleカレンダーの機能にプログラムからアクセスするためのRESTful APIです。このドキュメントでは、APIの主要な機能と利用可能なリソースについて説明します。

## 主要リソースタイプ

Google Calendar APIは以下の主要なリソースタイプを提供しています：

1. **Events（イベント）** - カレンダー上の予定やイベント
2. **Calendars（カレンダー）** - カレンダー自体の管理
3. **CalendarList（カレンダーリスト）** - ユーザーのカレンダーリスト
4. **Acl（アクセス制御リスト）** - カレンダーへのアクセス権限
5. **Freebusy（空き時間情報）** - 予定の空き状況の照会
6. **Settings（設定）** - ユーザー設定の管理
7. **Colors（色）** - カレンダーやイベントの色設定
8. **Channels（チャネル）** - 通知用のプッシュチャネル

## イベント（Events）の主な機能

イベントは最も重要なリソースで、以下の機能があります：

### 基本情報

- **summary**: イベントのタイトル
- **description**: イベントの説明
- **location**: イベントの場所
- **colorId**: イベントの色
- **start/end**: 開始・終了日時（dateTimeまたはdate形式）
- **timeZone**: タイムゾーン設定

### リマインダー設定

```json
"reminders": {
  "useDefault": false,
  "overrides": [
    {"method": "email", "minutes": 1440},  // 24時間前にメール
    {"method": "popup", "minutes": 30}     // 30分前にポップアップ
  ]
}
```

リマインダーの通知方法：
- **email**: メール通知
- **popup**: ポップアップ通知

### 繰り返し設定

- **recurrence**: RFC5545 iCalendar形式の繰り返しルール
  - 例: `["RRULE:FREQ=WEEKLY;UNTIL=20240630T000000Z;BYDAY=MO,WE,FR"]`
- **recurringEventId**: 繰り返しイベントのID

### 参加者管理

- **attendees**: 参加者リスト（メール、表示名、ステータスなど）
- **guestsCanInviteOthers**: 参加者が他の人を招待できるか
- **guestsCanModify**: 参加者がイベントを変更できるか
- **guestsCanSeeOtherGuests**: 参加者が他の参加者を見られるか

### ビデオ会議

- **conferenceData**: Google Meetなどのビデオ会議情報
- **hangoutLink**: Hangoutのリンク

### 添付ファイル

- **attachments**: イベントに添付されたファイル（Google Driveファイルなど）
  - 最大25個まで添付可能

### 特殊なイベントタイプ

- **eventType**: イベントの種類
  - **default**: 通常のイベント
  - **outOfOffice**: 外出中/不在
  - **focusTime**: 集中時間
  - **workingLocation**: 勤務場所

## カレンダー操作の主な機能

### イベント操作

- **events.insert**: 新規イベント作成
- **events.get**: イベント取得
- **events.list**: イベント一覧取得
- **events.update**: イベント更新
- **events.delete**: イベント削除
- **events.import**: 外部イベントのインポート
- **events.instances**: 繰り返しイベントのインスタンス取得
- **events.move**: イベントを別のカレンダーに移動
- **events.quickAdd**: テキストからの簡易イベント作成

### カレンダー管理

- **calendars.insert**: 新規カレンダー作成
- **calendars.get**: カレンダー情報取得
- **calendars.update**: カレンダー情報更新
- **calendars.delete**: カレンダー削除
- **calendars.clear**: カレンダーのイベントをすべて削除

### アクセス権限

- **acl.list**: アクセス権限一覧取得
- **acl.insert**: アクセス権限追加
- **acl.update**: アクセス権限更新
- **acl.delete**: アクセス権限削除

### その他の機能

- **freebusy.query**: 空き時間情報の照会
- **colors.get**: 利用可能な色の取得
- **settings.list**: ユーザー設定の取得

## 現在のプロジェクトでの実装状況

現在のプロジェクトでは、以下の機能が実装されています：

- イベントの作成（タイトル、場所、説明、開始・終了時間）
- イベントの取得・一覧表示
- イベントの更新
- イベントの削除
- イベントのキーワード検索

ただし、以下の機能は**未実装**です：

- **リマインダー設定**: イベント作成時にリマインダー（通知）を設定する機能
- **繰り返しイベント**: 定期的なイベントの作成・管理
- **参加者管理**: イベントへの参加者の招待・管理
- **ビデオ会議連携**: Google Meetなどのビデオ会議との連携

## 実装例：リマインダー設定の追加方法

イベント作成時にリマインダーを設定するには、以下のようにイベントオブジェクトに`reminders`プロパティを追加します：

```python
event = {
    "summary": title,
    "location": location,
    "description": description,
    "start": {
        "dateTime": start_time,
        "timeZone": "Asia/Tokyo",
    },
    "end": {
        "dateTime": end_time,
        "timeZone": "Asia/Tokyo",
    },
    "reminders": {
        "useDefault": False,
        "overrides": [
            {"method": "email", "minutes": 24 * 60},  # 1日前にメール
            {"method": "popup", "minutes": 30}        # 30分前にポップアップ
        ]
    }
}
```

## 参考リンク

- [Google Calendar API 概要](https://developers.google.com/workspace/calendar/api/guides/overview)
- [API リファレンス](https://developers.google.com/workspace/calendar/api/v3/reference)
- [イベントリソース](https://developers.google.com/workspace/calendar/api/v3/reference/events)
