import os
import asyncio
import requests
from telethon import TelegramClient, events

# ================= 設定區 (請修改這裡) =================

# 1. Telegram App 設定
API_ID = your_api_id_here
API_HASH = 'your_api_hash_here'

# 2. 機器人 Token
BOT_TOKEN = 'your_bot_token_here'

# 3. Discord 設定
DISCORD_WEBHOOK_URL = 'https://discord.com/api/webhooks/your_webhook_url_here'

# 4. 來源頻道 ID（範例: -1001234567890）
SOURCE_CHAT_ID = your_source_chat_id_here

# 5. 檔案大小限制 (Bytes) - Discord 目前限制 10MB
# 25MB = 25 * 1024 * 1024
MAX_FILE_SIZE = 25 * 1024 * 1024 

# ========================================================

client = TelegramClient('bot_session', API_ID, API_HASH)

def send_to_discord(username, text=None, file_path=None):
    """發送訊息到 Discord"""
    data = {
        "username": f"{username}", 
        "content": text if text else ""
    }
    try:
        if file_path:
            # 開啟檔案並發送
            with open(file_path, 'rb') as f:
                requests.post(DISCORD_WEBHOOK_URL, data=data, files={'file': f})
        else:
            requests.post(DISCORD_WEBHOOK_URL, json=data)
    except Exception as e:
        print(f"[發送失敗]: {e}")

@client.on(events.NewMessage)
async def handler(event):
    chat_id = event.chat_id
    
    # 1. 過濾頻道
    if SOURCE_CHAT_ID != 0 and chat_id != SOURCE_CHAT_ID:
        return

    # 2. 取得基本資訊
    chat = await event.get_chat()
    chat_title = chat.title if hasattr(chat, 'title') else "Unknown"
    
    print(f"★ 偵測到訊息 | 來源: {chat_title}")

    # 3. 準備內容
    msg_text = event.message.message or ""
    file_path = None
    
    # 建立訊息連結 (方便回頭找)
    # 如果是公開頻道，連結格式通常是 t.me/頻道名/ID
    msg_link = ""
    if hasattr(chat, 'username') and chat.username:
        msg_link = f"\n(來源連結: https://t.me/{chat.username}/{event.message.id})"

    # 4. 處理媒體 (圖片/影片/音訊)
    if event.message.media:
        # 檢查檔案大小
        if hasattr(event.message, 'file') and event.message.file:
            file_size = event.message.file.size
            file_name = event.message.file.name or "Unknown_File"
            
            if file_size > MAX_FILE_SIZE:
                # 檔案太大，只傳文字警告
                print(f"  -> 檔案過大 ({file_size/1024/1024:.2f} MB)，跳過下載。")
                msg_text += f"\n\n⚠️ [媒體檔案過大 ({file_size/1024/1024:.1f}MB)，無法上傳到 Discord]"
                msg_text += msg_link # 加上連結讓使用者可以點回去看
            else:
                # 檔案夠小，下載它
                print(f"  -> 正在下載媒體 ({file_size/1024/1024:.2f} MB)...")
                try:
                    file_path = await event.download_media()
                except Exception as e:
                    print(f"  -> 下載失敗: {e}")
                    msg_text += f"\n[媒體下載失敗]"

    # 5. 發送 (如果原本沒文字，只有大檔案被過濾掉，也要至少發送提示)
    if msg_text or file_path:
        send_to_discord(chat_title, msg_text, file_path)

    # 6. 清理
    if file_path and os.path.exists(file_path):
        os.remove(file_path)

# --- 主程式 ---
if __name__ == '__main__':
    async def main():
        print("Bot 啟動中...")
        await client.start(bot_token=BOT_TOKEN)
        print("Bot 已連線！")
        await client.run_until_disconnected()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("程式已停止")
    except Exception as e:
        print(f"發生錯誤: {e}")