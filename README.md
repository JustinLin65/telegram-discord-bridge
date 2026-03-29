# Telegram Discord Bridge
*本專案是我在經營 10K DOG 社群期間，為了在不同應用間同步訊息而開發的自動化工具。*

雙向訊息橋接工具，支援：
- Discord 頻道 -> Telegram 群組 / Topic
- Telegram 群組 / Topic -> Discord Webhook
- Telegram -> Telegram（raw forward / stripped copy）

## 核心功能

- 即時轉發文字、圖片、GIF、貼圖與附件
- Telegram Topic 過濾（`source_topic` / `target_topic`）
- 可設定是否轉發 Bot 訊息（`forward_bot_msg`）
- TG -> TG 支援 `raw` 與 `stripped` 模式
- TG -> DC 可自動套用 `ui-avatars.com` 頭像
- 檔案大小限制（`max_file_size`，單位 MB）
- 啟用 `debug` 後可輸出完整匹配資訊

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

## 設定檔（main_new.py）

`main_new.py` 會讀取兩個檔案：

- `dc2tg_config.json`：Discord -> Telegram 規則清單（陣列）
- `tg2dctg_config.json`：Telegram -> Discord / Telegram 全域設定（物件）

可參考：

- `dc2tg_config.json.example`
- `tg2dctg_config.json.example`

> 注意：JSON 正式格式不支援註解，使用前請移除所有 `#` 註解說明。

## 啟動

新版：

```bash
python main_new.py
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
- 支援Markdown語法同步
- 增加視覺化 GUI 介面
- 重構以增加「通用格式」層
