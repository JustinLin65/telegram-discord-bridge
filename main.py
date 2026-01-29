import os
import asyncio
import requests
from telethon import TelegramClient, events

# ================= 設定區 (請修改這裡) =================

# 1. Telegram App 設定
API_ID = your_api_id_here            
API_HASH = 'your_api_hash_here'     

# 2. 機器人 Token
# 請把從 BotFather 拿到的 Token 貼在下方
BOT_TOKEN = 'your_bot_token_here'

# 3. Discord 設定
DISCORD_WEBHOOK_URL = 'https://discord.com/api/webhooks/your_webhook_url_here'

# 4. 來源頻道設定 (Bot 模式建議直接填入 ID)
# 如果還不知道 ID，可以先填 0，Bot 也能幫忙查 ID
SOURCE_CHAT_ID = 0  # 範例: -1001234567890

# ========================================================

# 初始化 Client (注意：這裡不傳 session 名稱也沒關係，或隨便給一個)
client = TelegramClient('bot_session', API_ID, API_HASH)

def send_to_discord(username, text=None, file_path=None):
    """發送訊息到 Discord"""
    # Bot 轉發時，username 通常就是頻道名稱
    data = {
        "username": f"{username}", 
        "content": text if text else ""
    }
    try:
        if file_path:
            with open(file_path, 'rb') as f:
                requests.post(DISCORD_WEBHOOK_URL, data=data, files={'file': f})
        else:
            requests.post(DISCORD_WEBHOOK_URL, json=data)
    except Exception as e:
        print(f"[發送失敗]: {e}")

@client.on(events.NewMessage)
async def handler(event):
    chat_id = event.chat_id
    
    # 1. 過濾邏輯：只處理目標頻道的訊息
    if SOURCE_CHAT_ID != 0 and chat_id != SOURCE_CHAT_ID:
        return

    # 2. 取得資訊
    chat = await event.get_chat()
    chat_title = chat.title if hasattr(chat, 'title') else "Unknown"
    
    # 3. 在 CMD 顯示 (因為過濾過了，所以這裡只會顯示目標訊息)
    print(f"★ 收到新訊息 | 來源: {chat_title} | ID: {chat_id}")
    print(f"內容: {event.text[:50]}...")
    print("-" * 20)

    # 4. 準備轉發內容
    msg_text = event.message.message or ""
    file_path = None

    if event.message.media:
        # 下載圖片/媒體
        file_path = await event.download_media()

    # 5. 執行轉發
    if msg_text or file_path:
        send_to_discord(chat_title, msg_text, file_path)

    # 6. 清理檔案
    if file_path and os.path.exists(file_path):
        os.remove(file_path)

# --- 主程式 ---
if __name__ == '__main__':
    async def main():
        print("Bot 啟動中...")
        await client.start(bot_token=BOT_TOKEN)
        print("Bot 已連線！正在監聽指定頻道...")
        await client.run_until_disconnected()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("程式已停止")
    except Exception as e:
        print(f"發生錯誤: {e}")