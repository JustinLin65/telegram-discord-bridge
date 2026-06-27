# Telegram Discord Bridge v4.3.0
import aiosqlite
import discord
import aiohttp
import asyncio
import sys
import io
import re
import os
import json
import random
import urllib.parse
from telethon import TelegramClient, events, functions, types
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# ==================== 配置與路徑 ====================
DC2TG_CONFIG_FILE = 'dc2tg_config.json'
TG2DC_CONFIG_FILE = 'tg2dctg_config.json'
DB_PATH = 'message_map.db'

# ==================== 資料庫邏輯 ====================

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('PRAGMA journal_mode=WAL;')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS message_map (
                dc_msg_id INTEGER,
                dc_channel_id INTEGER,
                tg_msg_id INTEGER,
                tg_chat_id INTEGER,
                tg_top_id INTEGER,
                PRIMARY KEY (dc_msg_id, tg_msg_id)
            )
        ''')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_dc_msg ON message_map (dc_msg_id)')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_tg_msg ON message_map (tg_msg_id, tg_chat_id)')
        await db.commit()

async def save_mapping(dc_msg_id, dc_channel_id, tg_msg_id, tg_chat_id, tg_top_id=0):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                INSERT OR REPLACE INTO message_map 
                (dc_msg_id, dc_channel_id, tg_msg_id, tg_chat_id, tg_top_id) 
                VALUES (?, ?, ?, ?, ?)
            ''', (dc_msg_id, dc_channel_id, tg_msg_id, tg_chat_id, tg_top_id))
            await db.commit()
    except Exception as e:
        print(f"[!] 儲存 Mapping 失敗: {e}")

async def get_mappings_by_dc(dc_msg_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT tg_msg_id, tg_chat_id FROM message_map WHERE dc_msg_id = ?', (dc_msg_id,)) as cursor:
            return await cursor.fetchall()

async def get_mapping_by_tg(tg_msg_id, tg_chat_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT dc_msg_id, dc_channel_id FROM message_map WHERE tg_msg_id = ? AND tg_chat_id = ?', (tg_msg_id, tg_chat_id)) as cursor:
            return await cursor.fetchone()

async def delete_mapping_by_dc(dc_msg_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('DELETE FROM message_map WHERE dc_msg_id = ?', (dc_msg_id,))
        await db.commit()

async def delete_mapping_by_tg(tg_msg_id, tg_chat_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('DELETE FROM message_map WHERE tg_msg_id = ? AND tg_chat_id = ?', (tg_msg_id, tg_chat_id))
        await db.commit()

# 從 .env 讀取 Token
DISCORD_TOKEN = os.getenv('DC_BOT_TOKEN')
TELEGRAM_TOKEN = os.getenv('TG_BOT_TOKEN')
TG_API_ID = os.getenv('TG_API_ID')
TG_API_HASH = os.getenv('TG_API_HASH')

if TG_API_ID:
    TG_API_ID = int(TG_API_ID)

# 全域變數
DC2TG_RULES = []
TG2DC_CONFIG = None
SESSION = None  # 全域 aiohttp Session
DC_TO_TG_SEMAPHORE = None # 在 main 中初始化
TG_TO_DC_SEMAPHORE = None # 在 main 中初始化
DC_BOT_INSTANCE = None # 全域 Discord Bot 實例

# ==================== 設定檔載入邏輯 ====================

def load_all_configs():
    global DC2TG_RULES, TG2DC_CONFIG
    
    # 載入 Discord -> Telegram 規則
    if os.path.exists(DC2TG_CONFIG_FILE):
        try:
            with open(DC2TG_CONFIG_FILE, 'r', encoding='utf-8') as f:
                DC2TG_RULES = json.load(f)
                print(f"[V] 已載入 {DC2TG_CONFIG_FILE}: {len(DC2TG_RULES)} 條規則")
        except Exception as e:
            print(f"[!] 讀取 {DC2TG_CONFIG_FILE} 失敗: {e}")
    else:
        print(f"[!] 警告：找不到 {DC2TG_CONFIG_FILE}")

    # 載入 Telegram -> Discord/TG 規則
    if os.path.exists(TG2DC_CONFIG_FILE):
        try:
            with open(TG2DC_CONFIG_FILE, 'r', encoding='utf-8') as f:
                TG2DC_CONFIG = json.load(f)
                print(f"[V] 已載入 {TG2DC_CONFIG_FILE}")
        except Exception as e:
            print(f"[!] 讀取 {TG2DC_CONFIG_FILE} 失敗: {e}")
    else:
        print(f"[!] 警告：找不到 {TG2DC_CONFIG_FILE}")

# ==================== Discord 端的邏輯 (DC -> TG) ====================

class DiscordClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.emoji_pattern = re.compile(r'<(a?):(\w+):(\d+)>')

    async def on_ready(self):
        unique_channels = set(r["discord_channel_id"] for r in DC2TG_RULES)
        print(f'----------------------------------------')
        print(f'Discord 機器人已上線: {self.user}')
        print(f'監聽 Discord 頻道數: {len(unique_channels)} 個')
        print(f'----------------------------------------')

    async def download_file(self, url):
        try:
            async with SESSION.get(url) as resp:
                if resp.status == 200:
                    return io.BytesIO(await resp.read())
        except Exception as e:
            print(f"   [!] DC 下載失敗 ({url}): {e}")
        return None

    async def send_to_telegram(self, chat_id, thread_id, text, file_data=None, filename=None, send_type="document"):
        base_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
        for attempt in range(3):
            try:
                if file_data:
                    method = "sendPhoto" if send_type == "photo" else ("sendAnimation" if send_type == "animation" else "sendDocument")
                    file_field = "photo" if send_type == "photo" else ("animation" if send_type == "animation" else "document")
                    
                    data = aiohttp.FormData(quote_fields=False)
                    data.add_field('chat_id', str(chat_id))
                    data.add_field('caption', text)
                    data.add_field('parse_mode', 'Markdown')
                    if thread_id:
                        data.add_field('message_thread_id', str(thread_id))
                    
                    # 每次重試前確保游標在最前面
                    file_data.seek(0)
                    data.add_field(file_field, file_data, filename=filename or "file")
                    
                    async with SESSION.post(f"{base_url}/{method}", data=data) as resp:
                        res_json = await resp.json()
                else:
                    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown', 'disable_web_page_preview': True}
                    if thread_id: payload['message_thread_id'] = thread_id
                    async with SESSION.post(f"{base_url}/sendMessage", json=payload) as resp:
                        res_json = await resp.json()
                
                if resp.status == 200:
                    if not res_json.get("ok") and "IMAGE_PROCESS_FAILED" in res_json.get("description", "") and attempt == 0:
                        # 圖片處理失敗時嘗試以文件發送
                        return await self.send_to_telegram(chat_id, thread_id, text, file_data, filename, send_type="document")
                    return res_json
                elif resp.status == 429:
                    retry_after = res_json.get("parameters", {}).get("retry_after", 1)
                    print(f"   [!] Telegram 429，等待 {retry_after} 秒後重試...")
                    await asyncio.sleep(retry_after)
                elif resp.status >= 500:
                    print(f"   [!] Telegram 伺服器錯誤 ({resp.status})，重試中 ({attempt+1}/3)...")
                    await asyncio.sleep(2 ** attempt)
                else:
                    print(f"   [X] Telegram 請求失敗: {res_json}")
                    break
            except Exception as e:
                print(f"   [!] 發送至 Telegram 錯誤 (重試 {attempt+1}/3): {e}")
                await asyncio.sleep(2 ** attempt)
        return None

    async def on_message(self, message):
        if message.author.bot:
            return

        for rule in DC2TG_RULES:
            if message.channel.id == rule["discord_channel_id"]:
                # 使用 Semaphore 限制併發處理
                asyncio.create_task(self.wrapped_process_forward(message, rule))

    async def wrapped_process_forward(self, message, rule):
        async with DC_TO_TG_SEMAPHORE:
            await self.process_forward(message, rule)

    async def on_raw_message_delete(self, payload):
        mappings = await get_mappings_by_dc(payload.message_id)
        if mappings:
            print(f"[🗑️] 偵測到 Discord 訊息刪除: 頻道ID={payload.channel_id}, 訊息ID={payload.message_id}")
            for tg_msg_id, tg_chat_id in mappings:
                print(f"   -> 同步刪除 Telegram 訊息: 群組ID={tg_chat_id}, 訊息ID={tg_msg_id}")
                await self.delete_tg_message(tg_chat_id, tg_msg_id)
            await delete_mapping_by_dc(payload.message_id)

    async def delete_tg_message(self, chat_id, message_id):
        base_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
        payload = {'chat_id': chat_id, 'message_id': message_id}
        for attempt in range(3):
            try:
                async with SESSION.post(f"{base_url}/deleteMessage", json=payload) as resp:
                    res_json = await resp.json()
                    if resp.status == 200:
                        return res_json
                    elif resp.status == 429:
                        retry_after = res_json.get("parameters", {}).get("retry_after", 1)
                        await asyncio.sleep(retry_after)
                    elif resp.status >= 500:
                        await asyncio.sleep(2 ** attempt)
                    else:
                        break
            except Exception as e:
                print(f"[!] 刪除 Telegram 訊息失敗 (重試 {attempt+1}/3): {e}")
                await asyncio.sleep(2 ** attempt)
        return None

    async def process_forward(self, message, rule):
        header = f"*{message.author.display_name}*"
        tg_chat_id = rule["telegram_chat_id"]
        tg_topic_id = rule["telegram_topic_id"]
        content = message.content or ""

        async def handle_res(res):
            if res and res.get("ok"):
                await save_mapping(message.id, message.channel.id, res["result"]["message_id"], tg_chat_id, tg_topic_id)

        # 處理貼圖
        if message.stickers:
            for sticker in message.stickers:
                file_io = await self.download_file(sticker.url)
                if file_io:
                    stype = "animation" if sticker.format in [discord.StickerFormatType.apng, discord.StickerFormatType.gif] else "photo"
                    res = await self.send_to_telegram(tg_chat_id, tg_topic_id, f"{header}\n(貼圖: {sticker.name})", file_io, f"{sticker.name}.png", stype)
                    await handle_res(res)
            return

        # 處理自定義表情
        emojis = self.emoji_pattern.findall(content)
        if emojis and not content.replace(' '.join([f'<{a}:{n}:{i}>' for a, n, i in emojis]), '').strip():
            for is_animated, name, emoji_id in emojis:
                ext = "gif" if is_animated else "png"
                file_io = await self.download_file(f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}?size=512")
                if file_io:
                    res = await self.send_to_telegram(tg_chat_id, tg_topic_id, f"{header}\n(表情: {name})", file_io, f"{name}.{ext}", "animation" if is_animated else "photo")
                    await handle_res(res)
            return

        # 處理附件
        if message.attachments:
            for i, attachment in enumerate(message.attachments):
                file_io = io.BytesIO(await attachment.read())
                caption = f"{header}\n{content}".strip() if i == 0 else f"{header} (續)"
                stype = "photo" if attachment.content_type and attachment.content_type.startswith("image/") else "document"
                res = await self.send_to_telegram(tg_chat_id, tg_topic_id, caption, file_io, attachment.filename, stype)
                await handle_res(res)
            return

        # 處理 GIF
        if any(domain in content for domain in ["tenor.com", "giphy.com"]):
            media_url, embed_url = await self.wait_for_embed(message)
            if media_url:
                file_io = await self.download_file(media_url)
                if file_io:
                    clean_content = content.replace(embed_url, "").strip() if embed_url else content
                    res = await self.send_to_telegram(tg_chat_id, tg_topic_id, f"{header}\n{clean_content}".strip(), file_io, "animation.mp4", "animation")
                    await handle_res(res)
                    return

        if content:
            res = await self.send_to_telegram(tg_chat_id, tg_topic_id, f"{header}\n{content}".strip())
            await handle_res(res)

    async def wait_for_embed(self, message):
        for _ in range(5):
            try:
                message = await message.channel.fetch_message(message.id)
                if message.embeds:
                    for embed in message.embeds:
                        url = embed.video.url if embed.video else (embed.image.url if embed.image else None)
                        if url: return url, embed.url
            except:
                pass
            await asyncio.sleep(1.0)
        return None, None

# ==================== Telegram 端的邏輯 (TG -> DC/TG) ====================

tg_client = TelegramClient('integrated_bot_session', TG_API_ID, TG_API_HASH)

async def send_to_discord_webhook(webhook_url, username, text=None, file_path=None, avatar_url=None):
    # 加入 wait=true 以取得 Discord 訊息 ID
    url = webhook_url + ("&" if "?" in webhook_url else "?") + "wait=true"
    
    for attempt in range(3):
        data = aiohttp.FormData()
        data.add_field('username', username)
        if text: data.add_field('content', text)
        if avatar_url: data.add_field('avatar_url', avatar_url)
        if file_path:
            # 每次重試重新打開檔案以確保讀取位置正確
            data.add_field('file', open(file_path, 'rb'), filename=os.path.basename(file_path))
        
        try:
            async with SESSION.post(url, data=data) as resp:
                if resp.status in [200, 204]:
                    return await resp.json()
                elif resp.status == 429:
                    res_json = await resp.json()
                    retry_after = res_json.get("retry_after", 1)
                    print(f"   [!] Discord Webhook 429，等待 {retry_after} 秒後重試...")
                    await asyncio.sleep(retry_after)
                elif resp.status >= 500:
                    print(f"   [!] Discord 伺服器錯誤 ({resp.status})，重試中 ({attempt+1}/3)...")
                    await asyncio.sleep(2 ** attempt)
                else:
                    print(f"   [X] Discord Webhook 錯誤 ({resp.status}): {await resp.text()}")
                    break
        except Exception as e:
            print(f"   [X] Discord Webhook 發送失敗 (重試 {attempt+1}/3): {e}")
            await asyncio.sleep(2 ** attempt)
    return None

async def get_reply_tag(event):
    if not event.message.reply_to: return None
    try:
        reply_msg = await event.get_reply_message()
        if not reply_msg: return None
        raw_content = reply_msg.message or ""
        content_summary = (raw_content.replace('\n', ' ')[:20] + '...') if len(raw_content) > 20 else raw_content
        return f"💬 回覆: {content_summary}" if content_summary else "💬 回覆訊息"
    except: return "💬 回覆訊息"

async def tg_handler(event):
    if not TG2DC_CONFIG: return
    
    # 使用 Semaphore 限制併發處理
    async with TG_TO_DC_SEMAPHORE:
        chat_id = event.chat_id
        
        # 改進的 Topic ID 偵測邏輯
        current_topic_id = 0
        if event.message.reply_to:
            # 獲取配置中此群組所有已知的話題 ID (排除 0 和 1)
            known_topics = {
                p['source_topic'] for p in TG2DC_CONFIG.get("paths", [])
                if p.get('source_id') == chat_id and isinstance(p.get('source_topic'), int) and p['source_topic'] > 1
            }
            
            reply_obj = event.message.reply_to
            top_id = getattr(reply_obj, 'reply_to_top_id', None)
            msg_id = reply_obj.reply_to_msg_id
            
            if top_id:
                # 情況 A：在話題內部的回覆，使用官方 thread ID
                current_topic_id = top_id
            elif msg_id in known_topics:
                # 情況 B：回覆的是話題標題訊息，則該 msg_id 就是 Topic ID
                current_topic_id = msg_id
            else:
                # 情況 C：回覆的是普通訊息且非已知話題，視為 General (0)
                current_topic_id = 0

        sender = await event.get_sender()
        is_bot = getattr(sender, 'bot', False)
        fname = getattr(sender, 'first_name', '') or ''
        lname = getattr(sender, 'last_name', '') or ''
        sender_name = f"{fname} {lname}".strip() or getattr(sender, 'title', "User")

        # Debug 日誌：讓你知道現在偵測到什麼
        if TG2DC_CONFIG.get("debug", True):
            print(f"DEBUG | 收到訊息: Chat={chat_id} | Topic={current_topic_id} | From={sender_name}")

        for path in TG2DC_CONFIG.get("paths", []):
            if path['source_id'] == chat_id:
                # 判斷 Topic：設定為 0 (不限) 或者 ID 匹配
                # 增加特殊處理：如果設定為 1 但偵測到 0，通常是 General 主題
                match_topic = (path['source_topic'] == 0 or 
                              path['source_topic'] == current_topic_id or
                              (path['source_topic'] == 1 and current_topic_id == 0))
                
                if match_topic:
                    settings = path.get("settings", {})
                    if not settings.get("forward_bot_msg", True) and is_bot: continue

                    if path['target_type'] == "DC":
                        await forward_tg_to_dc(event, path, sender_name, is_bot)
                    elif path['target_type'] == "TG":
                        await forward_tg_to_tg(event, path, sender_name, is_bot)

async def forward_tg_to_dc(event, path, sender_name, is_bot):
    settings = path.get("settings", {})
    max_bytes = TG2DC_CONFIG.get("max_file_size", 25) * 1024 * 1024

    # 決定顯示名稱
    display_name = sender_name if settings.get("show_sender_name", True) else "Bridge Bot"

    avatar_url = None
    if settings.get("use_ui_avatars", False):
        avatar_url = f"https://ui-avatars.com/api/?name={urllib.parse.quote(display_name)}&background=random"

    msg_text = event.message.message or ""

    header_lines = []
    if settings.get("platform_prefix", False): header_lines.append("[TG]")
    if settings.get("show_reply_tag", False):
        tag = await get_reply_tag(event)
        if tag: header_lines.append(tag)
    
    full_text = ("\n".join(header_lines) + "\n" + msg_text).strip()
    
    file_path = None
    if event.message.file:
        # 取得檔案大小，如果為 None 則預設為 0 以避免比較錯誤
        file_size = event.message.file.size or 0
        if file_size <= max_bytes:
            file_path = await event.download_media()
        else:
            full_text += "\n\n⚠️ [媒體過大，未轉發]"

    res = await send_to_discord_webhook(path['target_id'], display_name, full_text, file_path, avatar_url)
    if res and "id" in res:
        # 取得 Topic ID (如果有)
        reply_obj = event.message.reply_to
        tg_top_id = getattr(reply_obj, 'reply_to_top_id', 0) or 0
        await save_mapping(int(res["id"]), int(res["channel_id"]), event.message.id, event.chat_id, tg_top_id)

    if file_path and os.path.exists(file_path): os.remove(file_path)

async def forward_tg_to_tg(event, path, sender_name, is_bot):
    settings = path.get("settings", {})
    if settings.get("forward_mode") == "raw":
        await tg_client(functions.messages.ForwardMessagesRequest(
            from_peer=event.chat_id, id=[event.message.id], to_peer=path['target_id'],
            top_msg_id=path['target_topic'] if path['target_topic'] != 0 else None,
            random_id=[random.randint(-2**63, 2**63-1)]
        ))
    else:
        msg_text = event.message.message or ""
        await tg_client.send_message(path['target_id'], f"**{sender_name}**:\n{msg_text}", 
                                     file=event.message.media, reply_to=path['target_topic'] or None)

async def tg_delete_handler(event):
    if not event.deleted_ids:
        return
    for msg_id in event.deleted_ids:
        mapping = await get_mapping_by_tg(msg_id, event.chat_id)
        if mapping:
            dc_msg_id, dc_channel_id = mapping
            print(f"[🗑️] 偵測到 Telegram 訊息刪除: 群組ID={event.chat_id}, 訊息ID={msg_id}")
            print(f"   -> 同步刪除 Discord 訊息: 頻道ID={dc_channel_id}, 訊息ID={dc_msg_id}")
            await delete_discord_message(dc_channel_id, dc_msg_id)
            await delete_mapping_by_tg(msg_id, event.chat_id)

async def delete_discord_message(channel_id, message_id):
    if DC_BOT_INSTANCE:
        try:
            channel = DC_BOT_INSTANCE.get_channel(channel_id) or await DC_BOT_INSTANCE.fetch_channel(channel_id)
            if channel:
                msg = await channel.fetch_message(message_id)
                await msg.delete()
        except Exception as e:
            # 忽略找不到訊息的錯誤 (可能已經被手動刪除)
            if "Unknown Message" not in str(e):
                print(f"[!] 刪除 Discord 訊息失敗: {e}")

# ==================== 主程式啟動 ====================

async def main():
    global SESSION, DC_TO_TG_SEMAPHORE, TG_TO_DC_SEMAPHORE
    await init_db()
    load_all_configs()
    
    if not all([DISCORD_TOKEN, TELEGRAM_TOKEN, TG_API_ID, TG_API_HASH]):
        print("[X] 錯誤：.env 缺少必要的 Token 或 API 資訊。")
        return

    # 初始化全域資源
    timeout = aiohttp.ClientTimeout(total=30)
    SESSION = aiohttp.ClientSession(timeout=timeout)
    DC_TO_TG_SEMAPHORE = asyncio.Semaphore(5)
    TG_TO_DC_SEMAPHORE = asyncio.Semaphore(5)

    intents = discord.Intents.default()
    intents.message_content = True
    global DC_BOT_INSTANCE
    DC_BOT_INSTANCE = DiscordClient(intents=intents)

    # 註冊 Telegram 事件處理器並加入過濾器
    if TG2DC_CONFIG and "paths" in TG2DC_CONFIG:
        source_ids = list(set(path['source_id'] for path in TG2DC_CONFIG["paths"]))
        tg_client.add_event_handler(tg_handler, events.NewMessage(chats=source_ids))
        tg_client.add_event_handler(tg_delete_handler, events.MessageDeleted(chats=source_ids))
        print(f"[V] Telegram 監聽頻道數: {len(source_ids)} 個")
    else:
        tg_client.add_event_handler(tg_handler, events.NewMessage)
        tg_client.add_event_handler(tg_delete_handler, events.MessageDeleted)

    print("正在啟動雙向轉發系統...")

    try:
        await asyncio.gather(
            DC_BOT_INSTANCE.start(DISCORD_TOKEN),
            tg_client.start(bot_token=TELEGRAM_TOKEN)
        )
        await tg_client.run_until_disconnected()
    except Exception as e:
        print(f"[X] 系統執行出錯: {e}")
    finally:
        if SESSION:
            await SESSION.close()
            print("[V] 已關閉全域 Session")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] 程式已手動停止")
