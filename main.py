import os
import asyncio
import requests
from telethon import TelegramClient, events

# ================= 設定區 (請修改這裡) =================

# 1. Telegram 設定
API_ID = your_api_id_here        
API_HASH = 'your_api_hash_here'     
BOT_TOKEN = 'your_bot_token_here'    

# 2. Discord 設定
DISCORD_WEBHOOK_URL = 'https://discord.com/api/webhooks/your_webhook_url_here'

# 3. 來源頻道 ID（範例: -1001234567890）
SOURCE_CHAT_ID = your_source_chat_id_here

# 4. 來源 Topic ID (特定論壇 ID)
# 如果填 0，代表「不篩選」，會轉發該頻道所有 Topic 的訊息
SOURCE_TOPIC_ID = your_source_topic_id_here

# 5. 檔案大小限制 (8MB)
MAX_FILE_SIZE = 8 * 1024 * 1024 

# ========================================================

client = TelegramClient('bot_session_dc', API_ID, API_HASH)

def send_to_discord(username, text=None, file_path=None):
    """發送訊息到 Discord"""
    # 這裡的 username 會顯示成 TG 發訊者的名字
    data = {
        "username": username, 
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
    
    # 1. 過濾頻道
    if SOURCE_CHAT_ID != 0 and chat_id != SOURCE_CHAT_ID:
        return

    # 2. 取得 Topic ID
    msg_topic_id = None
    if event.message.reply_to:
        msg_topic_id = event.message.reply_to.reply_to_top_id
        if not msg_topic_id:
            msg_topic_id = event.message.reply_to.reply_to_msg_id
    
    # ★ 補救措施：如果抓不到 ID，但在 Forum 頻道中，通常代表是 Topic 1 (General)
    if msg_topic_id is None:
        msg_topic_id = 1

    # 3. 過濾 Topic
    if SOURCE_TOPIC_ID != 0:
        # 如果目標是 1 (General)，接受 1 和 None (上面已經轉成 1 了)
        # 如果目標是其他 ID，則必須嚴格相等
        if msg_topic_id != SOURCE_TOPIC_ID:
            # (除錯) 印出來看看是誰被擋掉了
            # print(f"略過非目標 Topic: {msg_topic_id} (目標: {SOURCE_TOPIC_ID})")
            return

    # 4. 取得發訊者名稱 (維持原本邏輯)
    sender = await event.get_sender()
    display_name = "Unknown"
    
    if sender:
        fname = getattr(sender, 'first_name', '') or ''
        lname = getattr(sender, 'last_name', '') or ''
        title = getattr(sender, 'title', '') or ''
        
        if fname or lname:
            display_name = f"{fname} {lname}".strip()
        elif title:
            display_name = title
    else:
        chat = await event.get_chat()
        display_name = chat.title if hasattr(chat, 'title') else "TG Channel"

    print(f"★ 轉發 | Topic: {msg_topic_id} | 用戶: {display_name}")

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
                msg_text += f"\n\n⚠️ [媒體過大 ({file_size/1024/1024:.1f}MB)，未轉發]"
                msg_text += msg_link
            else:
                try:
                    file_path = await event.download_media()
                except Exception as e:
                    print(f"下載失敗: {e}")

    # 7. 發送
    if msg_text or file_path:
        send_to_discord(display_name, msg_text, file_path)

    if file_path and os.path.exists(file_path):
        os.remove(file_path)

# --- 主程式 ---
if __name__ == '__main__':
    async def main():
        print(f"TG -> DC 轉發器啟動 (Topic過濾: {SOURCE_TOPIC_ID})...")
        await client.start(bot_token=BOT_TOKEN)
        print("Bot 已連線！")
        await client.run_until_disconnected()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("程式已停止")
    except Exception as e:
        print(f"發生錯誤: {e}")