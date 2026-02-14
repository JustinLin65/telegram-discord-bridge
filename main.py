import os
import asyncio
import requests
import urllib.parse
from telethon import TelegramClient, events

# ==================== 設定區 ====================

API_ID = your_api_id_here
API_HASH = 'your_api_hash_here'     
BOT_TOKEN = 'your_bot_token_here'    

# -------------------------------------------------------
# 【規則清單 A】: Telegram -> Discord
# 設定哪些訊息要轉傳到 Discord Webhook
# -------------------------------------------------------
DC_FORWARD_RULES = [
    # --- 1: YOUR_DC_FORWARD_RULES_1 ---
    {
        "source_chat_id": your_source_chat_id_here,    # 來源頻道 ID
        "topic_id": your_source_topic_id_here,         # 來源 Topic ID (None 代表不分 Topic)
        "webhook_url": "https://discord.com/api/webhooks/your_webhook_url_here"
    },
    # --- 2: YOUR_DC_FORWARD_RULES_2 ---
    {
        "source_chat_id": your_source_chat_id_2_here,  # 來源頻道 ID
        "topic_id": your_source_topic_id_2_here,       # 來源 Topic ID (None 代表不分 Topic)
        "webhook_url": "https://discord.com/api/webhooks/your_webhook_url_2_here"
    },
    # --- 3: YOUR_DC_FORWARD_RULES_3 ---
    {
        "source_chat_id": your_source_chat_id_3_here,  # 來源頻道 ID
        "topic_id": your_source_topic_id_3_here,       # 來源 Topic ID (None 代表不分 Topic)
        "webhook_url": "https://discord.com/api/webhooks/your_webhook_url_3_here"
    },
]

# -------------------------------------------------------
# 【規則清單 B】: Telegram -> Telegram
# 設定哪些訊息要轉傳到另一個 TG 頻道/Topic
# -------------------------------------------------------
TG_FORWARD_RULES = [
    # --- 1. YOUR_TG_FORWARD_RULES ---
    {
        "source_chat_id": your_source_chat_id_here,  # 來源頻道
        "topic_id": your_source_topic_id_here,       # 來源 Topic ID (None 代表不分 Topic)
        "dest_chat_id": your_dest_chat_id_here,      # 目標頻道
        "dest_topic_id": your_dest_topic_id_here     # 目標 Topic ID (普通群組填 None)
    },
]

MAX_FILE_SIZE = 25 * 1024 * 1024            # 25MB 限制

# ========================================================

client = TelegramClient('bot_session_integrated', API_ID, API_HASH)

def send_to_discord(webhook_url, username, text=None, file_path=None, avatar_url=None):
    """發送訊息到指定的 Discord Webhook"""
    data = {
        "username": username,
        "content": text if text else ""
    }
    
    if avatar_url:
        data["avatar_url"] = avatar_url

    try:
        if file_path:
            with open(file_path, 'rb') as f:
                requests.post(webhook_url, data=data, files={'file': f})
        else:
            requests.post(webhook_url, json=data)
    except Exception as e:
        print(f"[Discord 發送失敗]: {e}")

def get_topic_id(event):
    """從事件中解析 Topic ID"""
    msg_topic_id = None
    if event.message.reply_to:
        msg_topic_id = event.message.reply_to.reply_to_top_id
        if not msg_topic_id:
            msg_topic_id = event.message.reply_to.reply_to_msg_id
    
    # 若抓不到 ID 但在 Topic 群組，預設歸類為 1 (General)
    if msg_topic_id is None:
        msg_topic_id = 1
        
    return msg_topic_id

@client.on(events.NewMessage)
async def handler(event):
    chat_id = event.chat_id
    current_topic_id = get_topic_id(event)
    
    # -------------------------------------------------
    # 邏輯 1: 處理 Discord 轉發 (DC_FORWARD_RULES)
    # -------------------------------------------------
    target_webhook = None
    for rule in DC_FORWARD_RULES:
        if rule['source_chat_id'] == chat_id:
            if rule['topic_id'] is None or rule['topic_id'] == current_topic_id:
                target_webhook = rule['webhook_url']
                break 

    # 如果有匹配到 DC 規則，準備資料並發送
    if target_webhook:
        await process_discord_forward(event, target_webhook, chat_id, current_topic_id)

    # -------------------------------------------------
    # 邏輯 2: 處理 Telegram 轉發 (TG_FORWARD_RULES)
    # -------------------------------------------------
    for rule in TG_FORWARD_RULES:
        if rule['source_chat_id'] == chat_id:
            if rule['topic_id'] is None or rule['topic_id'] == current_topic_id:
                # 執行 TG 轉發
                try:
                    await client.send_message(
                        rule['dest_chat_id'], 
                        event.message, 
                        reply_to=rule['dest_topic_id']
                    )
                    print(f"★ TG轉發成功 | Chat: {chat_id} | Topic: {current_topic_id} -> 目標 Chat: {rule['dest_chat_id']} | Topic: {rule['dest_topic_id']}")
                except Exception as e:
                    print(f"[TG 轉發錯誤]: {e}")

async def process_discord_forward(event, webhook_url, chat_id, topic_id):
    """處理 Discord 轉發的詳細邏輯 (生成頭像、下載媒體等)"""
    
    # 1. 取得發訊者資訊
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

    print(f"★ DC轉發 | Chat: {chat_id} | Topic: {topic_id} -> Webhook")

    # 2. 生成頭像
    encoded_name = urllib.parse.quote(display_name)
    avatar_url = f"https://ui-avatars.com/api/?name={encoded_name}&background=random&size=512&bold=true"

    # 3. 準備內容
    msg_text = event.message.message or ""
    file_path = None
    
    msg_link = ""
    chat = await event.get_chat()
    if hasattr(chat, 'username') and chat.username:
        msg_link = f"\n(Link: https://t.me/{chat.username}/{event.message.id})"

    # 4. 處理媒體
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

    # 5. 發送
    if msg_text or file_path:
        send_to_discord(webhook_url, display_name, msg_text, file_path, avatar_url)

    # 6. 清理檔案
    if file_path and os.path.exists(file_path):
        os.remove(file_path)

# --- 主程式 ---
if __name__ == '__main__':
    async def main():
        print(f"TG 同步機器人 (DC + TG) 啟動中...")
        await client.start(bot_token=BOT_TOKEN)
        print("Bot 已連線！正在監聽所有設定規則...")
        await client.run_until_disconnected()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("程式已停止")
    except Exception as e:
        print(f"發生錯誤: {e}")