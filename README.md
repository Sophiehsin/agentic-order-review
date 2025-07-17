# Agentic Order Review System

## 專案目標

本專案是一個**基於 Kafka 的容器化 Agentic 系統**，主要用於**保險訂單的智能審核**。系統結合了**黑名單過濾**與**AI 智能評估**，實現自動化的風險控管流程。

### 專案核心特色
- **Agentic 架構**：Consumer Agent 具備自主決策能力，能根據業務規則與 AI 評估自動審核訂單
- **微服務設計**：各服務獨立部署，透過 Kafka 進行解耦通訊
- **智能審核**：整合 GCP Gemini AI 進行資料合理性與風險評估
- **容器化部署**：使用 Docker Compose 一鍵啟動完整環境

---

## 環境部署與啟動方式

### 前置需求
- Docker Desktop
- Git

### 快速啟動
1*Clone 專案**
   ```bash
   git clone <your-repository-url>
   cd agentic-order-review
   ```
2. **設定環境變數**（選擇性）
   - 建立 `.env` 檔案，加入你的 GCP Gemini API Key（放置與 docker-compose 同一層）：
   ```bash
   GEMINI_API_KEY=your_api_key_here
   ```

3*一鍵啟動所有服務**
   ```bash
   docker-compose up --build
   ```

4. **開啟前端介面**
   - 瀏覽器開啟：http://localhost:8501## 服務端口
  - Streamlit 前端：http://localhost:8501
  - 黑名單 API：http://localhost:8000
  - Kafka：localhost:9092keeper**：localhost:2181

---

## 檔案架構說明

```
agentic-order-review/
├── docker-compose.yml          # 容器編排配置
├── README.md                   # 專案說明文件
├── .env                        # 環境變數（需自行建立）
│
├── producer/                   # 前端服務
│   ├── streamlit_app.py       # Streamlit 主程式
│   ├── kafka_utils.py         # Kafka 發送工具
│   ├── blacklist_utils.py     # 黑名單查詢工具
│   ├── requirements.txt       # Python 依賴
│   └── Dockerfile            # 容器配置
│
├── consumer/                   # Agent 服務
│   ├── main.py               # Consumer Agent 主程式
│   ├── gcp_gemini.py         # Gemini AI 整合
│   ├── requirements.txt      # Python 依賴
│   └── Dockerfile           # 容器配置
│
└── blacklist_api/             # 黑名單 API 服務
    ├── main.py              # FastAPI 主程式
    ├── blacklist.csv        # 黑名單資料
    ├── requirements.txt     # Python 依賴
    └── Dockerfile          # 容器配置
```

---

## 各服務角色與功能

### Streamlit 前端（Producer）**
**角色**：使用者介面與資料輸入
- **功能**：
  - 提供互動式保險訂單輸入表單
  - 基本資料合理性驗證（身分證、電話、email 等規則驗證）
  - 顯示審核結果與狀態
  - 側邊欄附有 GCP Gemini API 連線狀態檢查
- **技術**：Streamlit + Kafka Producer

### 2. **Consumer Agent**
**角色**：智能審核代理（本系統的核心 Agent）
- **功能**：
  - 自動從 Kafka 接收訂單訊息
  - 執行兩階段審核流程：
     1. **黑名單查詢**：呼叫 blacklist_api 確認是否為封鎖用戶
     2. **AI 風險評估**：呼叫 GCP Gemini API 進行資料合理性分析
  - 根據審核結果自動決策（通過/拒絕）
  - 將結果回寫至 Kafka 供前端查詢
- **技術**：Python + Kafka Consumer + GCP Gemini API

### 3. **黑名單 API（Blacklist API）**
**角色**：黑名單查詢服務
- **功能**：
  - 提供 REST API 查詢黑名單
  - 支援中英文姓名比對（不區分大小寫）
  - 回傳封鎖原因與狀態（若為黑名單）
- **技術**：FastAPI

### 4. **Kafka**
**角色**：訊息中介與事件驅動
- **功能**：
  - 作為 Producer 與 Consumer 之間的訊息佇列
  - 實現服務解耦與非同步處理
  - 支援高可用與擴展性
- **Topics**：
  - `orders`：訂單資料
  - `order_reviewed`：審核結果

### 5. **Zookeeper**
**角色**：Kafka 叢集協調服務
- **功能**：管理 Kafka 叢集狀態與配置

---

## 系統流程

1. **使用者輸入**：在 Streamlit 前端填寫訂單資料
2. **名單檢查**：系統先呼叫 blacklist_api 確認是否為封鎖用戶
3. **AI 評估**：若非黑名單，Consumer Agent 呼叫 GCP Gemini 進行風險評估
4. **結果回傳**：審核結果透過 Kafka 回傳至前端顯示

### 詳細判斷規則

#### 第一階段：黑名單檢查
- **檢查方式**：呼叫 `blacklist_api/check?name=xxx` API
- **比對規則**：支援中英文姓名比對（不區分大小寫、自動去除空白）
- **結果**：
  - 若在黑名單：直接拒絕，顯示封鎖原因
  - 若不在黑名單：進入下一階段

#### 第二階段：金額門檻判斷
- **門檻值**：年收入 ≥10,000 元
- **判斷邏輯**：
  - 若年收入 ≤ 10,000 直接標示拒絕，原因為「收入未達基礎條件」
  - 若年收入 >10,000：進入 AI 風險評估

#### 第三階段：AI 風險評估
- **AI 模型**：GCP Gemini 1.5 Pro
- **評估內容**：
  - 資料合理性檢查（姓名、職業、收入等是否合理）
  - 風險點識別（異常資料、矛盾資訊等）
  - 最終決策（通過/拒絕）與具體理由
- **回傳格式**：
  - 通過：`AI評估通過：<Gemini回傳內容>`
  - 拒絕：`AI評估拒絕：<Gemini回傳內容>`

#### 結果回傳
- 所有審核結果都會寫入 Kafka `order_reviewed` topic
- 前端會自動輪詢並顯示最終結果
- 明確標示結果來源（黑名單拒絕 / AI評估通過 / AI評估拒絕 / 收入未達基礎條件）

