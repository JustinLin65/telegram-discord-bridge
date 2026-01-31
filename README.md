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
- **身分識別**：會根據個人用戶（First/Last Name）或頻道身分（Title）自動切換顯示名稱。
- **大型檔案過濾**：新增 `MAX_FILE_SIZE` 檢查，自動跳過過大的媒體檔案，避免因 Discord 限制（目前為 25MB）導致的發送失敗。
- **訊息溯源連結**：自動生成 Telegram 來源連結，點擊即可跳轉回原頻道查看完整內容。
- **狀態監控**：終端機（CMD）現在會詳細顯示下載進度與跳過原因，方便維護。

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

- Discord Webhook:

    1. 在 Discord 頻道設定 -> 整合 -> 建立 Webhook 並複製網址。

3. **設定程式碼**
    
    開啟 `main.py`，修改 `設定區` 的內容：
    ```
    API_ID = 1234567                 # 填入你的 API ID
    API_HASH = 'your_hash'           # 填入你的 API Hash
    BOT_TOKEN = 'your_bot_token'     # 填入你的 Bot Token
    DISCORD_WEBHOOK_URL = '...'      # 填入 Discord Webhook 網址
    SOURCE_CHAT_ID = 0               # 填入來源頻道 ID
    OURCE_TOPIC_ID = 0               # 填入來源 topic ID
    MAX_FILE_SIZE = 25 * 1024 * 1024 # 檔案大小限制 (預設 25MB)
    ```

4. **啟動程式**

    `python main.py`

## ⚠️ 注意事項

檔案限制：Discord Webhook 的檔案上傳大小上限通常為 25MB，若 Telegram 檔案過大可能會發送失敗。

## 貢獻與反饋
如果在使用過程中遇到問題，或者有功能建議，歡迎隨時提出！