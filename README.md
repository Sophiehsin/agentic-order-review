# Agentic Order Review System

## 系統架構與各功能角色

- **Streamlit 前端（producer/streamlit_app.py）**
  - 提供互動式訂單輸入表單，欄位驗證嚴謹
  - 送出後先本地黑名單比對，再送入 Kafka `orders` topic
  - 可即時顯示審核結果

- **blacklist_api（blacklist_api/main.py）**
  - 提供 REST API 查詢黑名單，支援中英文姓名與原因
  - 讀取 `blacklist.csv`，可自訂黑名單

- **Consumer Agent（consumer/main.py）**
  - **本系統的 Agent**，自動從 Kafka 取訂單，進行審核
  - 工具使用：
    - 調用 blacklist_api 進行黑名單查詢
    - 調用 GCP Gemini API（目前為 mock，可串真實 API）
  - 根據規則自動決策，並將結果寫回 Kafka

- **Kafka**
  - 作為訊息中介，連接前端與後端 agent/consumer，實現 pub/sub 架構
  - 保證資料流動解耦、可擴展、可追蹤

## 一鍵啟動與環境佈署

1. 安裝 Docker Desktop
2. 下載/clone 專案
3. 於專案根目錄執行：
   ```bash
   docker-compose up --build
   ```
4. 於瀏覽器開啟 http://localhost:8501 使用前端表單

## 如何測試

1. 進入 http://localhost:8501 填寫訂單表單，送出後會自動進行黑名單與 AI 風險審核。
2. 若姓名（中或英）在黑名單，會顯示失敗與原因。
3. 若金額超過 10,000，會進行 AI 風險評估（目前為 mock，未來可串接 GCP Gemini）。
4. 審核結果會即時顯示於前端。

## 黑名單 API 說明

- **CSV 格式**（`blacklist_api/blacklist.csv`）：
  ```csv
  name_zh,name_en,reason
  聿欣,YU-HSIN,詐騙紀錄
  愛麗絲,ALICE SMITH,洗錢嫌疑
  八補,ROBERT BROWN,內部通報
  ```
- **API 查詢方式**：
  - Endpoint: `GET /check?name=xxx`
  - 支援中英文姓名查詢（自動忽略大小寫與空白）
  - 回傳範例：
    ```json
    {"blacklisted": true, "reason": "洗錢嫌疑"}
    ```

## GCP Gemini 風險評估
- 目前 consumer 端的 GCP Gemini API 為 mock 實作（隨機通過/拒絕，並回傳理由）。
- 若需串接真實 GCP Gemini，請於 consumer/gcp_gemini.py 裡補上 API key 與串接邏輯。
- 面試時如有 API key，可依需求調整。

## 設計討論與擴充性
- agentic consumer 可輕易擴充更多審核規則或串接外部工具
- 黑名單 API 支援多語姓名與原因，方便維護與查詢
- 所有服務皆已容器化，方便部署與測試
- Kafka 保證系統解耦與高可用

---

## 使用方式與專案流程說明

1. 使用者於前端（Streamlit）輸入訂單資料。
2. 系統會**先呼叫黑名單 API**，確認該使用者是否在黑名單中：
   - 若在黑名單，直接拒絕，並顯示封鎖原因。
   - 若不在黑名單，進入下一步。
3. 系統會**呼叫 GCP Gemini AI 進行風險與合理性評估**：
   - AI 會根據訂單內容判斷資料是否合理、是否有異常或風險。
   - AI 會給出通過/拒絕的決策與具體理由。
4. 最終審核結果（黑名單或 AI 決策）會即時顯示於前端。

此流程確保每一筆訂單都經過嚴謹的黑名單過濾與 AI 智能審核，提升風險控管與自動化效率。
