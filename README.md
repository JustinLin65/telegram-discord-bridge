# Telegram Discord Forwarder

*本專案是我在經營 10K DOG 社群期間，為了在不同應用間同步訊息而開發的自動化工具。*

這是一個基於 Python 開發的輕量級工具，能自動將指定 Telegram 頻道或群組的訊息（包含文字與媒體）同步轉發到 Discord 的指定頻道。

## 核心功能

- **即時監聽**：秒級同步轉發，不漏掉任何重要資訊。
- **多媒體支援**：除了純文字，還能自動下載並轉發圖片、影片及文件。
- **頻道過濾**：可設定特定的 `SOURCE_CHAT_ID`，僅轉發你需要的內容。
- **Topic 過濾**：支援 Telegram Forum 模式，可指定 `TARGET_TOPIC_ID`，只同步特定主題的訊息。
- **自動清理**：媒體檔案轉發後會自動從本地刪除，不佔用硬碟空間。
- **Webhook 整合**：無需複雜的 Discord Bot 權限，只要有 Webhook 連結即可運作。
- **身分識別**：會顯示發訊者的名稱，並整合 `ui-avatars.com` API 根據名稱自動生成對應的字母頭像。
- **大型檔案過濾**： `MAX_FILE_SIZE` 檢查，自動跳過過大的媒體檔案，避免因 Discord 限制（目前為 25MB）導致的發送失敗（若失敗會附上 Telegram 來源連結）。
- **狀態監控**：終端機（CMD）會詳細顯示下載進度與跳過原因，方便維護。

## 使用說明

1. **環境準備**

    請確保你的電腦已安裝 Python 3.7+。

    安裝必要的套件：

    `pip install telethon requests`

2. **取得憑證**

    在執行程式碼前，你需要準備以下資訊：

- Telegram API:

    1. 前往 ([my.telegram.org](https://my.telegram.org/)) 建立 App 並取得 `API_ID` 與 `API_HASH`。

- Bot Token:

    1. 在 Telegram 私訊 @BotFather 建立新機器人，並獲取 `BOT_TOKEN`。

    2. 注意：請將該機器人加入你想監聽的頻道並設為管理員。

- Telegram 頻道ID

    1. 在 Telegram 私訊 @userinfobot ，獲取頻道ID

- Discord Webhook:

    1. 在 Discord 頻道設定 -> 整合 -> 建立 Webhook 並複製網址。

3. **設定程式碼**
    
    開啟 `main.py`，修改 `設定區` 的內容：
    ```
    API_ID = 1234567                 # 填入你的 API ID
    API_HASH = 'your_hash'           # 填入你的 API Hash
    BOT_TOKEN = 'your_bot_token'     # 填入你的 Bot Token
    ```
    轉發規則：
    ```
    # -------------------------------------------------------
    # 【規則清單 A】: Telegram -> Discord
    # 設定哪些訊息要轉傳到 Discord Webhook
    # -------------------------------------------------------
        # --- 1: YOUR_DC_FORWARD_RULES_1 ---
        {
            "source_chat_id": 0,     # 來源頻道 ID
            "topic_id": 0,           # 來源 Topic ID (None 代表不分 Topic)
            "webhook_url": "..."     # 填入 Discord Webhook 網址
        },

    # -------------------------------------------------------
    # 【規則清單 B】: Telegram -> Telegram
    # 設定哪些訊息要轉傳到另一個 TG 頻道/Topic
    # -------------------------------------------------------
        # --- 1. YOUR_TG_FORWARD_RULES ---
        {
            "source_chat_id": 0,     # 來源頻道
            "topic_id": 0,           # 來源 Topic ID (None 代表不分 Topic)
            "dest_chat_id": 0,       # 目標頻道
            "dest_topic_id": 0       # 目標 Topic ID (普通群組填 None)
        },
    
    MAX_FILE_SIZE = 25 * 1024 * 1024 # 檔案大小限制 (預設 25MB)(根據需求自行修改)
    ```

4. **啟動程式**

    `python main.py`

## ⚠️ 注意事項

檔案限制：Discord Webhook 的檔案上傳大小上限通常為 25MB，若 Telegram 檔案過大可能會發送失敗。
Ps：超過裝置可用儲存空間也可能失敗！

## 貢獻與反饋
如果在使用過程中遇到問題，或者有功能建議，歡迎隨時提出！