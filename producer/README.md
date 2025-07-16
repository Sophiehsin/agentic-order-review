# Producer (Streamlit 前端)

## 功能說明
- 以 Streamlit 提供互動式訂單輸入表單
- 根據保險種類顯示不同欄位
- 送出後先本地黑名單比對，再呼叫 GCP Gemini API 風險評估
- 通過則送入 Kafka `orders` topic，失敗則顯示理由

## 啟動方式
1. 安裝 Docker Desktop
2. 於 producer 資料夾下執行：
   ```bash
   docker build -t producer-streamlit .
   docker run -p 8501:8501 --env KAFKA_BOOTSTRAP_SERVERS=kafka:9092 producer-streamlit
   ```
   或於 docker-compose.yml 中設定對應服務
3. 於瀏覽器開啟 http://localhost:8501

## API/模組說明
- `streamlit_app.py`：主程式，表單與審核流程
- `blacklist_utils.py`：本地黑名單查詢
- `gemini_api.py`：GCP Gemini API 風險評估（mock）
- `kafka_utils.py`：Kafka 發送工具
- `blacklist.csv`：黑名單資料（需自行建立） 