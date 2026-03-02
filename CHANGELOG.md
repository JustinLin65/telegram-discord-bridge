# Changelog

本專案的所有顯著變更將記錄在此檔案中。
格式參考自 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/)。

## [2.1.0] - 2026

### Added
- **除錯模式 (DEBUG_MODE)**：新增全域除錯開關，開啟後可顯示所有傳入訊息的詳細資訊（Chat ID, Topic ID, Bot 判定），簡化設定流程。
- **機器人過濾邏輯**：在轉發規則中新增 `ignore_bots` 選項，可自定義是否過濾掉來源頻道的機器人訊息，有效防止 Bot-to-Bot 迴圈。
- **Raw API 支援**：TG 轉 TG 轉發改用 `functions.messages.ForwardMessagesRequest`。
    - **優點**：保留原始訊息的轉發來源標籤。
    - **穩定性**：新增自動回退機制，若 Raw API 調用失敗將自動切換回 `send_message` (Copy Mode)。
- **萬用匹配 (Wildcard Support)**：`topic_id` 現在支援設定為 `0`。當設為 `0` 時，系統將忽略主題判斷，轉發該頻道下的所有訊息。
- **頭像自定義**：Discord 規則新增 `use_avatar` 開關，使用者可選擇顯示發訊者頭像或維持 Webhook 預設圖示。

### Changed
- **邏輯結構優化**：重構了 `handler` 內的規則匹配流程，現在能更精確地處理多重規則重疊的情況。
- **錯誤處理強化**：針對媒體下載與網路請求加入更多 `try-except` 保護，提升程式長時間運行的穩定性。

### Fixed
- **Topic ID 抓取修正**：修正了在特定 Forum 群組下無法正確取得 `reply_to_top_id` 的邊緣案例。

## [2.0.0]

### Added
- **雙軌轉發架構**：同步支援 `DC_FORWARD_RULES` (TG 轉 Discord) 與 `TG_FORWARD_RULES` (TG 轉 TG) 兩套獨立規則。
- **整合式非同步處理**：引入 `process_discord_forward` 函式，將發訊者識別、頭像生成、媒體下載與 Webhook 發送邏輯封裝，提升執行效率。

### Changed
- **Session 名稱整合**：更新內部 Session 名稱為 `bot_session_integrated`，以對應全新的整合邏輯。

## [1.3.0]

### Added
- **自動化頭像生成系統**：整合 `ui-avatars.com` 服務。現在 Webhook 會根據 `display_name` 自動生成並顯示首字母頭像，且背景顏色隨機，增加視覺辨識度。
- **URL 編碼處理**：引入 `urllib.parse` 處理中文名稱的 URL 編碼，確保非英文名稱也能正確生成頭像連結。

### Changed
- **Session 名稱優化**：更改內部 Session 名稱為 `bot_session_auto_avatar`，確保升級後能乾淨啟動並重新儲存狀態。
- **程式碼結構優化**：在 `send_to_discord` 函數中新增 `avatar_url` 參數支援。

## [1.2.0]

### Added
- **Topic 過濾功能**：新增 `TARGET_TOPIC_ID` 參數，支援 Telegram 論壇模式的精確同步。
- **Forum 補救邏輯**：針對 Forum 模式下首個主題（General）可能無法獲取 ID 的限制，加入自動偵測補償機制。
- **發訊者識別**：重寫了 `display_name` 邏輯，現在能更準確地抓取「名+姓」或「頻道標題」作為 Discord 的顯示名稱。

### Changed
- **Discord 顯示優化**：Discord 訊息的 Webhook Username 現在會顯示為 TG 實際發訊者的名稱，而非統一的機器人名稱，使同步感更真實。

## [1.1.0]

### Added
- **檔案大小限制機制**：新增 `MAX_FILE_SIZE` 設定，避免發送超過 Discord 限制（25MB）的大檔案造成程式崩潰。
- **訊息來源連結**：如果轉發失敗自動附加 Telegram 原始訊息連結，方便使用者溯源。
- **詳細日誌輸出**：在終端機（CMD）增加詳細的運行狀態顯示，包含下載進度、檔案過濾原因及錯誤提示。

### Changed
- **媒體處理邏輯**：優化了下載流程，僅在檔案大小符合規範時才會啟動下載，節省系統資源。
- **訊息提示機制**：若檔案過大被過濾，會在 Discord 端發送提示訊息，確保資訊同步不中斷。

---

## [1.0.0]

### Added
- 專案初始版本發佈。
- 實現 Telegram 訊息監聽與 Discord Webhook 基本同步功能。
- 支援圖片、影片及文件的自動轉發。
- 提供基礎的頻道 ID 過濾功能。
- 檔案發送後的自動清理機制，保持運行環境整潔。