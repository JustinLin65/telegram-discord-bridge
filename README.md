# Telegram Discord Bridge

*本專案是我在經營 10K DOG 社群期間，為了在不同應用間同步訊息而開發的自動化工具。*

這是一個基於 Python 開發的輕量級工具，能自動將指定 Telegram 頻道或群組的訊息（包含文字與媒體）同步轉發到 Discord Webhook 或另一個 Telegram 頻道/主題。

## 核心功能

- **即時監聽**：秒級同步轉發，不漏掉任何重要資訊。
- **多媒體支援**：除了純文字，還能自動下載並轉發圖片、影片及文件。
- **頻道/Topic過濾**：可設定特定的 `source_chat_id` 和 `topic_id`，僅轉發你需要的內容。
- **自動清理**：媒體檔案轉發後會自動從本地刪除，不佔用硬碟空間。
- **Webhook 整合**：無需複雜的 Discord Bot 權限，只要有 Webhook 連結即可運作。
- **身分識別**：會顯示發訊者的名稱，並整合 `ui-avatars.com` API 根據名稱自動生成對應的字母頭像（可關閉）。
- **機器人過濾**：`ignore_bots` 可選擇是否忽略其他機器人的訊息，避免無限迴圈或無用雜訊。
- **雙模轉發**：TG -> TG 支援 **Raw API (保留轉發標籤)** 與 **Copy Mode (自定義標頭)** 雙模式。
- **大型檔案過濾**：自動跳過超過 25MB 的檔案，並附上原始 Telegram 連結，確保不因 Discord 限制而崩潰。
- **除錯模式**：`DEBUG_MODE` 可即時監控所有收到的訊息 ID 與 Topic 資訊，方便設定規則。

## 使用說明

1. **環境準備**

    請確保你的電腦已安裝 Python 3.7+。

    安裝必要的套件：

    `pip install -r requirements.txt`

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
    
   在專案根目錄建立 `.env` 檔案，填入以下資訊：
    ```
    TG_API_ID=your_api_hash_here
    TG_API_HASH=your_api_hash_here
    TG_BOT_TOKEN=your_bot_token_here
    ```
    並參考 config.json.example 建立 config.json，確保移除非標準 JSON 的註解文字（如 # 號部分）。
    ```
    {
      "debug": true,                            # 是否啟用除錯模式，啟用後將輸出更詳細日誌
      "max_file_size": 25,                      # 最大文件大小，單位MB
      "paths": [
        {
          "name": "1. YOUR_TG_FORWARD_RULES",   # 規則名稱
          "source_id": -1001234567890,          # 來源頻道ID
          "source_topic": 1234,                 # 來源主題ID，沒有主題則為0
          "target_type": "TG",                  # 目標平台，TG或DC
          "target_id": -1001234567890,          # 目標頻道ID或DC Webhook URL
          "target_topic": 123,                  # 目標主題ID，沒有主題則為0
          "settings": {
            "forward_mode": "raw",              # 轉發模式，raw或stripped，raw僅對TG目標有效
            "use_ui_avatars": false,            # 是否使用ui-avatars.com，僅對DC目標有效
            "show_sender_name": false,          # 是否顯示發送者名稱，僅對DC目標有效
            "avatar_blacklist": ["Justin Lin"], # 頭像黑名單，以顯示名稱辨別。包含的用戶頭像將不會被轉發，僅對DC目標有效
            "platform_prefix": false,           # 是否在訊息前添加平台前綴，僅對DC目標有效
            "forward_bot_msg": false,           # 是否轉發機器人訊息，僅對TG目標有效
            "show_reply_tag": false             # 是否在轉發的訊息中添加回覆標籤
          }
        }
      ]
    }
    ```

4. **啟動程式**

    `python main.py`

## ⚠️ 注意事項

- 權限：機器人必須是來源頻道與目標頻道的管理員（Admin），確保有查看和發送訊息的權限。
- 格式：config.json 格式必須完全正確，否則程式會拒絕啟動以保護運行安全。
- 格式2：標準的 JSON 格式不支援任何形式的註解。正式運行時不可包含 `#` 及其後的內容。
- 檔案限制：Discord Webhook 的檔案上傳大小上限通常為 25MB，若 Telegram 檔案過大可能會發送失敗。
Ps：超過裝置可用儲存空間也可能失敗！

## 貢獻與反饋
如果在使用過程中遇到問題，或者有功能建議，歡迎隨時提出！