import os
import asyncio
import requests
import urllib.parse
from telethon import TelegramClient, events

# ================= 設定區 =================

API_ID = your_api_id_here            
API_HASH = 'your_api_hash_here'     
BOT_TOKEN = 'your_bot_token_here'    
DISCORD_WEBHOOK_URL = 'https://discord.com/api/webhooks/your_webhook_url_here'

SOURCE_CHAT_ID = your_source_chat_id_here   # 來源頻道 ID
TARGET_TOPIC_ID = your_target_topic_id_here # 目標 Topic ID (General通常是1)
MAX_FILE_SIZE = 25 * 1024 * 1024            # 25MB 限制

# =========================================

# session 名稱改一下，確保乾淨啟動
client = TelegramClient('bot_session_auto_avatar', API_ID, API_HASH)

def send_to_discord(username, text=None, file_path=None, avatar_url=None):
    """發送訊息到 Discord (包含自動頭像)"""
    data = {
        "username": username,
        "content": text if text else ""
    }
    
    # 只要有 avatar_url 就加入
    if avatar_url:
        data["avatar_url"] = avatar_url

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
    
    # 1. 過濾頻道
    if SOURCE_CHAT_ID != 0 and chat_id != SOURCE_CHAT_ID:
        return

    # 2. Topic 處理 (包含 Topic 1 的修正邏輯)
    msg_topic_id = None
    if event.message.reply_to:
        msg_topic_id = event.message.reply_to.reply_to_top_id
        if not msg_topic_id:
            msg_topic_id = event.message.reply_to.reply_to_msg_id
    
    # 如果抓不到 ID，預設為 1 (General)
    if msg_topic_id is None:
        msg_topic_id = 1

    # 過濾 Topic
    if TARGET_TOPIC_ID != 0:
        if msg_topic_id != TARGET_TOPIC_ID:
            return

    # 3. 取得發訊者資訊 (作為顯示名稱)
    sender = await event.get_sender()
    display_name = "Unknown"
    
    if sender:
        fname = getattr(sender, 'first_name', '') or ''
        lname = getattr(sender, 'last_name', '') or ''
        title = getattr(sender, 'title', '') or ''
        
        if fname or lname:
            # 組合名字
            display_name = f"{fname} {lname}".strip()
        elif title:
            # 如果是頻道身分
            display_name = title
    else:
        chat = await event.get_chat()
        display_name = chat.title if hasattr(chat, 'title') else "TG Channel"

    print(f"★ 轉發 | Topic: {msg_topic_id} | 用戶: {display_name}")

    # 4. 【核心功能】自動生成頭像 URL
    # 將名字進行 URL 編碼
    encoded_name = urllib.parse.quote(display_name)
    
    # 組合 API 網址
    # background=random: 背景顏色隨機
    # size=512: 解析度
    # bold=true: 字體加粗
    avatar_url = f"https://ui-avatars.com/api/?name={encoded_name}&background=random&size=512&bold=true"

    # 5. 準備內容
    msg_text = event.message.message or ""
    file_path = None
    
    msg_link = ""
    chat = await event.get_chat()
    if hasattr(chat, 'username') and chat.username:
        msg_link = f"\n(Link: https://t.me/{chat.username}/{event.message.id})"

    # 6. 處理媒體
    if event.message.media:
        if hasattr(event.message, 'file') and event.message.file:
            file_size = event.message.file.size
            if file_size > MAX_FILE_SIZE:
                msg_text += f"\n\n⚠️ [媒體過大，未轉發]"
                msg_text += msg_link
            else:
                try:
                    file_path = await event.download_media()
                except Exception as e:
                    print(f"下載失敗: {e}")

    # 7. 發送
    if msg_text or file_path:
        send_to_discord(display_name, msg_text, file_path, avatar_url)

    if file_path and os.path.exists(file_path):
        os.remove(file_path)

# --- 主程式 ---
if __name__ == '__main__':
    async def main():
        print(f"TG -> DC (全自動頭像版) 啟動中...")
        await client.start(bot_token=BOT_TOKEN)
        print("Bot 已連線！")
        await client.run_until_disconnected()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("程式已停止")
    except Exception as e:
        print(f"發生錯誤: {e}")