# Changelog

本專案的所有顯著變更將記錄在此檔案中。
格式參考自 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/)。

## [3.1]

### Added
- **自動化頭像生成系統**：整合 `ui-avatars.com` 服務。現在 Webhook 會根據 `display_name` 自動生成並顯示首字母頭像，且背景顏色隨機，增加視覺辨識度。
- **URL 編碼處理**：引入 `urllib.parse` 處理中文名稱的 URL 編碼，確保非英文名稱也能正確生成頭像連結。

### Changed
- **Session 名稱優化**：更改內部 Session 名稱為 `bot_session_auto_avatar`，確保升級後能乾淨啟動並重新儲存狀態。
- **程式碼結構優化**：在 `send_to_discord` 函數中新增 `avatar_url` 參數支援。

## [3.0]

### Added
- **Topic 過濾功能**：新增 `TARGET_TOPIC_ID` 參數，支援 Telegram 論壇模式的精確同步。
- **Forum 補救邏輯**：針對 Forum 模式下首個主題（General）可能無法獲取 ID 的限制，加入自動偵測補償機制。
- **發訊者識別**：重寫了 `display_name` 邏輯，現在能更準確地抓取「名+姓」或「頻道標題」作為 Discord 的顯示名稱。

### Changed
- **Discord 顯示優化**：Discord 訊息的 Webhook Username 現在會顯示為 TG 實際發訊者的名稱，而非統一的機器人名稱，使同步感更真實。

## [2.0]

### Added
- **檔案大小限制機制**：新增 `MAX_FILE_SIZE` 設定，避免發送超過 Discord 限制（25MB）的大檔案造成程式崩潰。
- **訊息來源連結**：如果轉發失敗自動附加 Telegram 原始訊息連結，方便使用者溯源。
- **詳細日誌輸出**：在終端機（CMD）增加詳細的運行狀態顯示，包含下載進度、檔案過濾原因及錯誤提示。

### Changed
- **媒體處理邏輯**：優化了下載流程，僅在檔案大小符合規範時才會啟動下載，節省系統資源。
- **訊息提示機制**：若檔案過大被過濾，會在 Discord 端發送提示訊息，確保資訊同步不中斷。

---

## [1.0]

### Added
- 專案初始版本發佈。
- 實現 Telegram 訊息監聽與 Discord Webhook 基本同步功能。
- 支援圖片、影片及文件的自動轉發。
- 提供基礎的頻道 ID 過濾功能。
- 檔案發送後的自動清理機制，保持運行環境整潔。