import os
import asyncio
import json
import requests
import urllib.parse
import random
import sys
from telethon import TelegramClient, events, functions, types
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數
load_dotenv()

# ==================== 環境變數讀取區 ====================
API_ID = os.getenv('TG_API_ID')
if API_ID:
    API_ID = int(API_ID)

API_HASH = os.getenv('TG_API_HASH')
BOT_TOKEN = os.getenv('TG_BOT_TOKEN')

if not all([API_ID, API_HASH, BOT_TOKEN]):
    print("錯誤：請確保 .env 檔案中已正確填寫 TG_API_ID, TG_API_HASH 與 TG_BOT_TOKEN")
    sys.exit(1)

# ==================== 全域設定 ====================
CONFIG_FILE = 'config.json'
CONFIG = None  # 用於儲存啟動時讀取的設定

def load_config_strictly():
    """啟動時嚴格讀取設定檔，若有錯誤直接停止程式"""
    if not os.path.exists(CONFIG_FILE):
        print(f"   [X] 啟動失敗：找不到設定檔 {CONFIG_FILE}")
        sys.exit(1)

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                print(f"   [X] 啟動失敗：{CONFIG_FILE} 內容為空")
                sys.exit(1)
            
            # 讀取 JSON
            config_data = json.loads(content)
            print(f"   [V] 設定檔載入成功。")
            return config_data
            
    except json.JSONDecodeError as e:
        print(f"   [X] 啟動失敗：{CONFIG_FILE} 語法錯誤")
        print(f"   [!] 錯誤細節: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"   [X] 啟動失敗：讀取設定檔時發生意外錯誤: {e}")
        sys.exit(1)

# ========================================================

client = TelegramClient('bot_session_integrated', API_ID, API_HASH)

def send_to_discord(webhook_url, username, text=None, file_path=None, avatar_url=None):
    """發送訊息到指定的 Discord Webhook"""
    data = {"username": username, "content": text if text else ""}
    if avatar_url:
        data["avatar_url"] = avatar_url

    try:
        if file_path:
            with open(file_path, 'rb') as f:
                requests.post(webhook_url, data=data, files={'file': f}, timeout=15)
        else:
            requests.post(webhook_url, json=data, timeout=15)
    except Exception as e:
        print(f"   [X] Discord 發送失敗: {e}")

def get_topic_id(event):
    """從事件中解析 Topic ID (message_thread_id)"""
    msg_topic_id = None
    if event.message.reply_to:
        msg_topic_id = event.message.reply_to.reply_to_top_id
        if not msg_topic_id:
            msg_topic_id = event.message.reply_to.reply_to_msg_id
    return msg_topic_id or 0 # 預設為 0

async def get_reply_tag(event):
    """取得回覆訊息的標籤與摘要，精確區分 Topic 系統歸類與真實回覆"""
    if not event.message.reply_to:
        return None
    
    reply_to = event.message.reply_to
    top_id = getattr(reply_to, 'reply_to_top_id', None)
    msg_id = getattr(reply_to, 'reply_to_msg_id', None)
    
    is_real_reply = False
    
    if top_id is not None:
        if msg_id != top_id:
            is_real_reply = True
        else:
            try:
                reply_msg = await event.get_reply_message()
                if reply_msg and isinstance(reply_msg.action, types.MessageActionTopicCreated):
                    is_real_reply = True
                else:
                    is_real_reply = False
            except:
                is_real_reply = False
    else:
        is_real_reply = True

    if not is_real_reply:
        return None

    try:
        reply_msg = await event.get_reply_message()
        if not reply_msg:
            return None
            
        raw_content = reply_msg.message or ""
        if not raw_content and reply_msg.media:
            content_summary = "[媒體訊息]"
        elif not raw_content and isinstance(reply_msg.action, types.MessageActionTopicCreated):
            content_summary = f"[建立主題: {reply_msg.action.title}]"
        else:
            clean_content = raw_content.replace('\n', ' ').strip()
            content_summary = (clean_content[:20] + '...') if len(clean_content) > 20 else clean_content
            
        return f"💬 回覆: {content_summary}" if content_summary else "💬 回覆訊息"
    except:
        return "💬 回覆訊息"

@client.on(events.NewMessage)
async def handler(event):
    if not CONFIG:
        return

    chat_id = event.chat_id
    current_topic_id = get_topic_id(event)
    DEBUG_MODE = CONFIG.get("debug", False)
    
    sender = await event.get_sender()
    is_bot = getattr(sender, 'bot', False)
    
    sender_name = "Unknown"
    if sender:
        fname = getattr(sender, 'first_name', '') or ''
        lname = getattr(sender, 'last_name', '') or ''
        sender_name = f"{fname} {lname}".strip() or getattr(sender, 'title', "User")

    if DEBUG_MODE:
        print(f"DEBUG | 收到: Chat={chat_id} | Topic={current_topic_id} | From={sender_name} | Bot={is_bot}")

    for path in CONFIG.get("paths", []):
        if path['source_id'] == chat_id:
            if path['source_topic'] == 0 or path['source_topic'] == current_topic_id:
                if path['target_type'] == "DC":
                    await process_dc_path(event, path, sender_name, is_bot)
                elif path['target_type'] == "TG":
                    await process_tg_path(event, path, sender_name, is_bot)

async def process_dc_path(event, path, sender_name, is_bot):
    settings = path.get("settings", {})
    if not settings.get("forward_bot_msg", True) and is_bot:
        return

    # 1. 取得檔案大小限制 (MB 轉 bytes)
    max_bytes = CONFIG.get("max_file_size", 25) * 1024 * 1024

    # 2. 預先建構訊息連結
    msg_link = ""
    try:
        chat = await event.get_chat()
        if hasattr(chat, 'username') and chat.username:
            msg_link = f"\n(Link: https://t.me/{chat.username}/{event.message.id})"
    except:
        pass

    # 3. 處理頭像
    use_avatar = settings.get("use_ui_avatars", False)
    avatar_blacklist = settings.get("avatar_blacklist", [])
    avatar_url = None
    if use_avatar and sender_name not in avatar_blacklist:
        encoded_name = urllib.parse.quote(sender_name)
        avatar_url = f"https://ui-avatars.com/api/?name={encoded_name}&background=random&size=512&bold=true"

    display_name = sender_name if settings.get("show_sender_name", True) else "TG Bot"
    msg_text = event.message.message or ""
    
    # 4. 組合標頭 (Prefix, Name, Reply Tag)
    header_lines = []
    has_prefix = settings.get("platform_prefix", False)
    has_name = settings.get("show_sender_name", True)
    
    if has_prefix and has_name:
        header_lines.append(f"[TG] {sender_name}")
    elif has_prefix:
        header_lines.append("[TG]")
    
    if settings.get("show_reply_tag", False):
        reply_tag = await get_reply_tag(event)
        if reply_tag:
            header_lines.append(reply_tag)

    if header_lines:
        msg_text = "\n".join(header_lines) + "\n" + msg_text

    # 5. 媒體下載與大小判定
    file_path = None
    if event.message.media:
        if hasattr(event.message, 'file') and event.message.file:
            if event.message.file.size <= max_bytes:
                try:
                    file_path = await event.download_media()
                except Exception as e:
                    print(f"   [!] 媒體下載失敗: {e}")
            else:
                # 媒體過大處理邏輯
                msg_text += f"\n\n⚠️ [媒體過大，未轉發]{msg_link}"

    send_to_discord(path['target_id'], display_name, msg_text, file_path, avatar_url)
    
    if file_path and os.path.exists(file_path):
        os.remove(file_path)

async def process_tg_path(event, path, sender_name, is_bot):
    settings = path.get("settings", {})
    if not settings.get("forward_bot_msg", True) and is_bot:
        return

    max_bytes = CONFIG.get("max_file_size", 25) * 1024 * 1024

    try:
        if settings.get("forward_mode") == "raw":
            await client(functions.messages.ForwardMessagesRequest(
                from_peer=event.chat_id,
                id=[event.message.id],
                to_peer=path['target_id'],
                top_msg_id=path['target_topic'] if path['target_topic'] != 0 else None,
                random_id=[random.randint(-9223372036854775808, 9223372036854775807)]
            ))
        else:
            # 複製模式 (stripped)
            msg_text = event.message.message or ""
            
            # 預先建構連結 (供過大媒體使用)
            msg_link = ""
            try:
                chat = await event.get_chat()
                if hasattr(chat, 'username') and chat.username:
                    msg_link = f"\n(Link: https://t.me/{chat.username}/{event.message.id})"
            except: pass

            header_lines = []
            has_prefix = settings.get("platform_prefix", False)
            has_name = settings.get("show_sender_name", False)
            
            if has_prefix and has_name:
                header_lines.append(f"[TG] {sender_name}")
            elif has_prefix:
                header_lines.append("[TG]")
            elif has_name:
                header_lines.append(sender_name)
                
            if settings.get("show_reply_tag", False):
                reply_tag = await get_reply_tag(event)
                if reply_tag:
                    header_lines.append(reply_tag)

            if header_lines:
                msg_text = "\n".join(header_lines) + "\n" + msg_text

            # 媒體大小檢查
            media_to_send = event.message.media
            if media_to_send and hasattr(event.message, 'file') and event.message.file:
                if event.message.file.size > max_bytes:
                    media_to_send = None
                    msg_text += f"\n\n⚠️ [媒體過大，未轉發]{msg_link}"

            await client.send_message(
                path['target_id'],
                msg_text,
                file=media_to_send,
                reply_to=path['target_topic'] if path['target_topic'] != 0 else None
            )
        print(f"   [V] {path['name']} 轉發成功")
    except Exception as e:
        print(f"   [X] {path['name']} 轉發失敗: {e}")

if __name__ == '__main__':
    async def main():
        global CONFIG
        print("正在讀取設定檔...")
        CONFIG = load_config_strictly()
        print("正在啟動 Telegram Bot...")
        await client.start(bot_token=BOT_TOKEN)
        print("Bot 已連線！正在監聽訊息...")
        await client.run_until_disconnected()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("程式已停止")
    except Exception as e:
        print(f"發生嚴重錯誤: {e}")