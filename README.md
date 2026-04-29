# Telegram Discord Bridge

*本專案是我在經營 10K DOG 社群期間，為了在不同應用間同步訊息而開發的自動化工具。*

雙向訊息橋接工具，支援：

- Discord 頻道 -> Telegram 群組 / Topic
- Telegram 群組 / Topic -> Discord Webhook
- Telegram -> Telegram（raw forward / stripped copy）

## 核心功能

- **即時轉發**：支援文字、圖片、GIF、貼圖與附件。
- **雙向橋接**：Discord <-> Telegram 整合。
- **效能優化**：採用 **Global Session Pool** 複用連線，降低延遲與資源開銷。
- **穩定性控制**：引入 **Concurrency Control (Semaphore)** 限制併發任務，防止速率限制。
- **精確識別**：Telegram Topic / Thread 優化識別（精確匹配 `source_topic`）。
- **高度自定義**：支援發送者名稱控制、頭像自動生成（UI Avatars）、檔案大小限制（`max_file_size`）。
- **靈活過濾**：可設定是否轉發 Bot 訊息，並支援多種 TG -> TG 轉發模式。
- **偵錯友善**：啟用 `debug` 模式後可輸出完整匹配資訊與處理日誌。

## 技術亮點

- **Connection Pooling**: 透過 `aiohttp.ClientSession` 全域管理，減少頻繁建立/關閉 TCP 連線的握手開銷，這在轉發大量圖片或頻繁通訊時非常有感。
- **Concurrency Limiting**: 使用 `asyncio.Semaphore` 將並行處理數限制在安全範圍內（預設 5），有效避免在瞬間爆量訊息時被 Telegram/Discord API 暫時封鎖或耗盡系統 Socket 資源。
- **Event Filter**: 在 Telegram 端採用 `chats` 篩選器，讓機器人只對特定群組的事件產生反應，而非監聽所有加入的群組再進行過濾，極大地優化了大型帳號下的運作效率。

## 安裝

1. 安裝 Python 3.9+
2. 安裝依賴：

```bash
pip install discord.py aiohttp telethon python-dotenv
```

## 環境變數

請在專案根目錄建立 `.env`（可由 `.env.example` 複製）：

```bash
TG_API_ID=12345678
TG_API_HASH='your_telegram_api_hash'
TG_BOT_TOKEN='your_telegram_bot_token'
DC_BOT_TOKEN='your_discord_bot_token'
```

## 設定檔

本程式會自動載入以下兩個 JSON 配置：

- `dc2tg_config.json`：Discord -> Telegram 規則（Array）
- `tg2dctg_config.json`：Telegram -> Discord / Telegram 全域設定（Object）

> 注意：JSON 格式不支援註解，使用前請移除所有說明文字。

## 啟動

```bash
python main.py
```

## 權限與注意事項

- Discord Bot 需要讀取訊息與附件權限（並啟用 Message Content Intent）
- Telegram Bot 需要在目標群組/頻道有足夠發送權限
- Discord Webhook 上傳大小通常受伺服器等級限制
- 若訊息含大型媒體，程式會依 `max_file_size` 跳過並保留文字提示

## 貢獻與反饋

如果在使用過程中遇到問題，或者有功能建議，歡迎隨時提出！

## 未來 Roadmap

- [ ] 支援讀取 YAML 配置
- [ ] 支援 Markdown 語法同步
- [ ] 增加視覺化 GUI 介面
- [ ] 重構以增加「通用格式」層 (Common Message Schema)
