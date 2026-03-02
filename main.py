import os
import asyncio
import requests
import urllib.parse
import random
from telethon import TelegramClient, events, functions

# ==================== 使用者設定區 ====================

API_ID = your_api_id_here
API_HASH = 'your_api_hash_here'
BOT_TOKEN = 'your_bot_token_here'

# 【除錯模式】
# True = 顯示所有 Bot 收到的訊息資訊 (可用來查 ID)
# False = 只顯示成功轉發的訊息 (正式運行用)
DEBUG_MODE = True

# -------------------------------------------------------
# 【規則清單 A】: Telegram -> Discord
# -------------------------------------------------------
DC_FORWARD_RULES = [
    # --- 1: YOUR_DC_FORWARD_RULES_1---
    {
        "ignore_bots": True,                            # [過濾] True=不轉發機器人訊息
        "use_avatar": True,                             # [頭像] True=顯示使用者名字頭像, False=顯示預設機器人圖示
        "source_chat_id": your_source_chat_id_here,     # 來源頻道 ID
        "topic_id": your_topic_id_here,                 # 來源 Topic ID
        "webhook_url": "https://discord.com/api/webhooks/your_webhook_url_here"     # Discord Webhook URL
    },
    # --- 2: YOUR_DC_FORWARD_RULES_2 ---
    {
        "ignore_bots": True,
        "use_avatar": True,
        "source_chat_id": your_source_chat_id_here,
        "topic_id": your_topic_id_here,
        "webhook_url": "https://discord.com/api/webhooks/your_webhook_url_here"
    },
]

# -------------------------------------------------------
# 【規則清單 B】: Telegram -> Telegram
# -------------------------------------------------------
TG_FORWARD_RULES = [
    # --- 1.YOUR_TG_FORWARD_RULES_1 ---
    {
        "ignore_bots": False,                           # [過濾] True=不轉發機器人訊息
        "source_chat_id": your_source_chat_id_here,     # 來源頻道
        "topic_id": your_source_topic_id_here,          # 來源 Topic ID
        "dest_chat_id": your_dest_chat_id_here,         # 目標頻道
        "dest_topic_id": your_dest_topic_id_here        # 目標 Topic ID
    },
]

MAX_FILE_SIZE = 25 * 1024 * 1024                        # 25MB 檔案大小限制

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
        print(f"   [X] Discord 發送失敗: {e}")

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
    # 1. 取得基本資訊
    chat_id = event.chat_id
    current_topic_id = get_topic_id(event)
    
    # 2. 取得發送者 (兼容性處理)
    sender = await event.get_sender()
    is_bot = getattr(sender, 'bot', False)

    # 3. 【除錯訊息】
    if DEBUG_MODE:
        sender_title = "Unknown"
        if sender:
            sender_title = getattr(sender, 'title', None) or \
                           getattr(sender, 'first_name', None) or \
                           "User"
        print(f"DEBUG | 收到: Chat={chat_id} | Topic={current_topic_id} | Bot={is_bot} | Title={sender_title}")

    # -------------------------------------------------
    # 邏輯 1: 處理 Discord 轉發
    # -------------------------------------------------
    target_webhook = None
    use_avatar = True 

    for rule in DC_FORWARD_RULES:
        if rule['source_chat_id'] == chat_id:
            # [修改] 加入 0 的判斷：None 或 0 都視為全部轉發
            if rule['topic_id'] is None or rule['topic_id'] == 0 or rule['topic_id'] == current_topic_id:
                if rule.get("ignore_bots", True) and is_bot:
                    continue

                target_webhook = rule['webhook_url']
                use_avatar = rule.get("use_avatar", True)
                break 

    if target_webhook:
        await process_discord_forward(event, target_webhook, chat_id, current_topic_id, use_avatar)

    # -------------------------------------------------
    # 邏輯 2: 處理 Telegram 轉發 (Forward 模式)
    # -------------------------------------------------
    for i, rule in enumerate(TG_FORWARD_RULES):
        if rule['source_chat_id'] == chat_id:
            
            # [修改] 加入 0 的判斷：None 或 0 都視為全部轉發
            if rule['topic_id'] is None or rule['topic_id'] == 0 or rule['topic_id'] == current_topic_id:
                
                # --- 檢查 機器人過濾 ---
                if rule.get("ignore_bots", True) and is_bot:
                    if DEBUG_MODE: print(f"   -> [跳過] 偵測到機器人訊息")
                    continue
                
                # --- 執行轉發 ---
                try:
                    # 【核心修改】使用 Raw API 以支援 Topic 並保留標籤
                    # 這是最穩定的方法，可以繞過 telethon 版本的限制
                    await client(functions.messages.ForwardMessagesRequest(
                        from_peer=chat_id,
                        id=[event.message.id],
                        to_peer=rule['dest_chat_id'],
                        top_msg_id=rule['dest_topic_id'] if rule['dest_topic_id'] else None,
                        random_id=[random.randint(-9223372036854775808, 9223372036854775807)]
                    ))
                    print(f"   [V] TG轉發成功! (Raw API) -> 目標: {rule['dest_chat_id']} (Topic {rule['dest_topic_id']})")
                
                except TypeError:
                    # 萬一 Raw API 也不支援 (極罕見)，回退到 copy 模式
                    print("   [!] Raw API 不支援此環境，回退至 Copy 模式 (無標籤)...")
                    try:
                        await client.send_message(
                            rule['dest_chat_id'],      
                            event.message,             
                            reply_to=rule['dest_topic_id']
                        )
                        print(f"   [V] TG轉發成功 (Copy Mode) -> 目標: {rule['dest_chat_id']} (Topic {rule['dest_topic_id']})")
                    except Exception as e:
                        print(f"   [X] TG轉發失敗 (Copy Mode): {e}")

                except Exception as e:
                    print(f"   [X] TG轉發失敗: {e}")

            else:
                # --- Topic 不符的提示 ---
                if DEBUG_MODE:
                    print(f"   -> [跳過] Topic不符。規則設定: {rule['topic_id']} vs 實際收到: {current_topic_id}")

async def process_discord_forward(event, webhook_url, chat_id, topic_id, use_avatar):
    """處理 Discord 轉發詳細邏輯"""
    
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

    print(f"   [V] 觸發 Discord 轉發 -> Webhook")

    avatar_url = None
    if use_avatar:
        encoded_name = urllib.parse.quote(display_name)
        avatar_url = f"https://ui-avatars.com/api/?name={encoded_name}&background=random&size=512&bold=true"

    msg_text = event.message.message or ""
    file_path = None
    
    msg_link = ""
    try:
        chat = await event.get_chat()
        if hasattr(chat, 'username') and chat.username:
            msg_link = f"\n(Link: https://t.me/{chat.username}/{event.message.id})"
    except:
        pass

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
                    print(f"   [!] 媒體下載失敗: {e}")

    if msg_text or file_path:
        send_to_discord(webhook_url, display_name, msg_text, file_path, avatar_url)

    if file_path and os.path.exists(file_path):
        os.remove(file_path)

# --- 主程式 ---
if __name__ == '__main__':
    async def main():
        print(f"TGDC 雙向整合機器人 (Debug模式: {DEBUG_MODE}) 啟動中...")
        await client.start(bot_token=BOT_TOKEN)
        print("Bot 已連線！正在監聽訊息...")
        await client.run_until_disconnected()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("程式已停止")
    except Exception as e:
        print(f"發生錯誤: {e}")