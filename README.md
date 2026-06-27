# Telegram Discord Bridge

*本專案是我在經營 10K DOG 社群期間，為了在不同應用間同步訊息而開發的自動化工具。*

雙向訊息橋接工具，支援：

- Discord 頻道 -> Telegram 群組 / Topic
- Telegram 群組 / Topic -> Discord Webhook
- Telegram -> Telegram（raw forward / stripped copy）

## 核心功能

- **即時轉發**：支援文字、圖片、GIF、貼圖與附件。
- **雙向橋接**：Discord <-> Telegram 整合。
- **雙向刪除同步**：當任何一端（Discord 或 Telegram）的訊息被刪除時，另一端相對應的轉發訊息也會自動同步刪除。
- **效能優化**：採用 **Global Session Pool** 複用連線，降低延遲與資源開銷。
- **穩定性控制**：引入 **雙向獨立併發控制 (DC/TG Separated Semaphore)** 與 **API 自動重試/容錯機制**，防止頻率限制並極大提升橋接穩定性。
- **精確識別**：Telegram Topic / Thread 優化識別（精確匹配 `source_topic`）。
- **高度自定義**：支援發送者名稱控制、頭像自動生成（UI Avatars）、檔案大小限制（`max_file_size`）。
- **靈活過濾**：可設定是否轉發 Bot 訊息，並支援多種 TG -> TG 轉發模式。
- **偵錯友善**：啟用 `debug` 模式後可輸出完整匹配資訊與處理日誌。

## 技術亮點

- **Connection Pooling**: 透過 `aiohttp.ClientSession` 全域管理，減少頻繁建立/關閉 TCP 連線的握手開銷，這在轉發大量圖片或頻繁通訊時非常有感。
- **Concurrency Limiting**: 重構為雙向獨立的 `asyncio.Semaphore` 機制（各限制為 5），分別控制 Discord -> Telegram 與 Telegram -> Discord 的併發數，避免單向瞬間爆量負載耗盡限制而導致另一向轉發阻塞。
- **Auto Retry & Rate Limit Handling**: 針對 Telegram Bot API 與 Discord Webhook API 請求導入最多 3 次自動重試邏輯。支援自動識別與處理 HTTP 429 速率限制（讀取 `retry_after` 並等待重試）及 5xx 伺服器錯誤（指數退避重試，間隔 `2 ** attempt` 秒），並在重試時自動重設檔案指針/重新開啟檔案以確保上傳完整性，大幅提升高負載與邊緣網路下的強健性。
- **Event Filter**: 在 Telegram 端採用 `chats` 篩選器，讓機器人只對特定群組的事件產生反應，而非監聽所有加入的群組再進行過濾，極大地優化了大型帳號下的運作效率。
- **Bidirectional Deletion Sync & SQLite DB**: 使用 SQLite (`aiosqlite`) 對照資料庫 `message_map.db`。當任一端刪除訊息時，會比對資料庫中的訊息 ID 映射關係，自動精確同步刪除另一端發送的轉發訊息，免除手動清理的麻煩。

## 安裝

1. 安裝 Python 3.9+
2. 安裝依賴：

```bash
pip install -r requirements.txt
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

- 支援讀取 YAML 配置
- 支援 Markdown 語法同步
- 增加視覺化 GUI 介面
- 重構以增加「通用格式」層 (Common Message Schema)
- 定時自動清理資料庫
