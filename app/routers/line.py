import os
from fastapi import APIRouter, Request, BackgroundTasks
from linebot.v3.webhooks import MessageEvent, PostbackEvent
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks.models import TextMessageContent
from linebot.v3.webhook import WebhookParser

from app.services.group_scheduler import process_vote, close_voting
from app.services.google_calendar import check_user_auth_status
from app.services.langgraph_processor import process_user_message

router = APIRouter(prefix="/line", tags=["line"])

line_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "dummy_token")
line_secret = os.getenv("LINE_CHANNEL_SECRET", "dummy_secret")

configuration = Configuration(access_token=line_token)


@router.post("/callback")
async def callback(request: Request, background_tasks: BackgroundTasks):
    signature = request.headers.get('X-Line-Signature', '')
    body = await request.body()
    body_decode = body.decode('utf-8')
    
    # デバッグ情報を出力
    print(f"LINE Webhook received - Signature: {signature[:10]}...")
    print(f"LINE_CHANNEL_SECRET: {line_secret[:5]}...")
    print(f"Body length: {len(body_decode)} bytes")
    
    try:
        # イベントを解析して非同期処理
        parser = WebhookParser(line_secret)
        events = parser.parse(body_decode, signature)
        print(f"Successfully parsed {len(events)} events")
        for event in events:
            if isinstance(event, MessageEvent) and isinstance(event.message, TextMessageContent):
                # バックグラウンドタスクとしてメッセージ処理を実行
                background_tasks.add_task(process_message_async, event)
            elif isinstance(event, PostbackEvent):
                # ポストバックイベントを処理
                background_tasks.add_task(handle_postback, event)
    except InvalidSignatureError as e:
        print(f"Invalid signature error: {e}")
        # 署名エラーでも200を返す（LINEプラットフォームの要件）
        return {"message": "OK"}
    except Exception as e:
        print(f"Unexpected error in LINE webhook: {e}")
        # その他のエラーでも200を返す
        return {"message": "OK"}
    
    # 即座に200 OKを返す
    return {"message": "OK"}


async def process_message_async(event):
    """メッセージを非同期で処理する"""
    try:
        user_id = event.source.user_id
        user_message = event.message.text
        
        # ユーザーの認証状態を確認
        is_authenticated = check_user_auth_status(user_id)
        
        if not is_authenticated and any(keyword in user_message for keyword in 
                                       ["カレンダー", "予定", "会議", "ミーティング", "スケジュール"]):
            auth_url = f"{os.getenv('APP_BASE_URL')}/google/authorize?user_id={user_id}"
            reply_text = (f"Googleカレンダーへのアクセス許可が必要です。"
                         f"以下のリンクから認証を行ってください。\n{auth_url}")
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                reply_message_request = ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_text)]
                )
                line_bot_api.reply_message(reply_message_request)
        elif is_authenticated:
            # AIプロセッサを使用してメッセージを処理
            response = process_user_message(user_id, user_message)
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                reply_message_request = ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=response)]
                )
                line_bot_api.reply_message(reply_message_request)
        else:
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                reply_message_request = ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="こんにちは！カレンダーの予定を管理するには、"
                                              "「予定」「スケジュール」などのキーワードを含むメッセージを送ってください。")]
                )
                line_bot_api.reply_message(reply_message_request)
    except Exception as e:
        print(f"Error in async message processing: {e}")
        try:
            with ApiClient(configuration) as api_client:
                line_bot_api = MessagingApi(api_client)
                reply_message_request = ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="申し訳ありません。メッセージ処理中にエラーが発生しました。"
                                              "後でもう一度お試しください。")]
                )
                line_bot_api.reply_message(reply_message_request)
        except Exception:
            # リプライトークンの有効期限が切れている可能性がある
            pass


async def handle_postback(event):
    """ポストバックイベントを処理する"""
    user_id = event.source.user_id
    postback_data = event.postback.data

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        if postback_data.startswith("vote_"):
            parts = postback_data.split("_", 5)
            if len(parts) >= 6:
                _, group_id, event_title, option_index, start_time, end_time = parts

                success = process_vote(
                    user_id=user_id,
                    group_id=group_id,
                    event_title=event_title,
                    option_index=int(option_index),
                    start_time=start_time,
                    end_time=end_time,
                )

                if success:
                    line_bot_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=event.reply_token,
                            messages=[TextMessage(text=f"{event_title}の日程に投票しました。")],
                        )
                    )
                else:
                    line_bot_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=event.reply_token,
                            messages=[TextMessage(text="投票処理中にエラーが発生しました。")],
                        )
                    )

        elif postback_data.startswith("close_vote_"):
            parts = postback_data.split("_", 3)
            if len(parts) >= 4:
                _, _, group_id, event_title = parts

                success = close_voting(group_id=group_id, event_title=event_title, line_bot_api=line_bot_api)

                if success:
                    line_bot_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=event.reply_token,
                            messages=[
                                TextMessage(
                                    text=f"{event_title}の投票を締め切りました。最も多く投票された日時が選択されました。"
                                )
                            ],
                        )
                    )
                else:
                    line_bot_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=event.reply_token,
                            messages=[TextMessage(text="投票締め切り処理中にエラーが発生しました。")],
                        )
                    )
