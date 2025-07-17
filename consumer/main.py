import os
import time
import json
import requests
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import NoBrokersAvailable
from gcp_gemini import review_with_gemini

KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
ORDERS_TOPIC = 'orders'
REVIEWED_TOPIC = 'order_reviewed'
BLACKLIST_API_URL = os.getenv('BLACKLIST_API_URL', 'http://localhost:8000/check')
GCP_API_KEY = os.getenv('GEMINI_API_KEY', '')

# Retry loop for KafkaConsumer initialization
for _ in range(10):
    try:
        consumer = KafkaConsumer(
            ORDERS_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id='order-review-group'
        )
        break
    except NoBrokersAvailable as e:
        print(f"Kafka 連線失敗，3秒後重試: {e}")
        time.sleep(3)
else:
    print("無法連上 Kafka，consumer 結束")
    exit(1)

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def check_blacklist(customer_name):
    try:
        resp = requests.get(BLACKLIST_API_URL, params={'name': customer_name})
        return resp.json().get('blacklisted', False)
    except Exception as e:
        print(f"Blacklist API error: {e}")
        return False

def main():
    for msg in consumer:
        order = msg.value
        print(f"[DEBUG] Received order: {order}")
        customer_name = order.get('name') or order.get('customer_name')
        amount = order.get('amount') or order.get('income', 0)
        # Step 1: 黑名單查詢
        print(f"[DEBUG] Checking blacklist for: {customer_name}")
        if check_blacklist(customer_name):
            result = {
                'order': order,
                'status': 'rejected',
                'reason': '黑名單拒絕'
            }
            print(f"[DEBUG] Blacklist hit: {result}")
            producer.send(REVIEWED_TOPIC, result)
            continue
        # Step 2
        if amount < 10000:
            # 收入未達基礎條件，直接拒絕
            result = {
                'order': order,
                'status': 'rejected',
                'reason': '收入未達基礎條件'
            }
            print(f"[DEBUG] Income too low: {result}")
            producer.send(REVIEWED_TOPIC, result)
            continue
        # Step3訂單進行 AI 評估
        # GCP Gemini API 審核，帶入 system prompt
        system_prompt = (
            "你是一個嚴格的保險訂單審核員，請根據下列資料判斷：\n"
            "1. 此資料是否合理存在於真實世界，還是有明顯亂填、虛構、矛盾或不合常理之處？\n"
            "2. 若有風險或異常，請明確指出風險點與原因。\n"
            "3. 最後請明確說明此訂單是否可通過，並給出具體理由。\n"
            "請直接回覆審核意見，不要重複本指示。\n"
            "\n【範例1】\n資料：{'name': '王小明', 'income': 500000, 'job': '工程師', ...}\n回覆：通過。資料合理，收入與職業相符，無明顯異常。\n"
            "\n【範例2】\n資料：{'name': 'AAA', 'income': 99999999, 'job': '學生', ...}\n回覆：拒絕。姓名疑似亂填，年收入與職業不符，資料不合理。\n"
            "\n【本次資料】\n資料："
        )
        print(f"[DEBUG] Calling GCP Gemini for: {order}")
        gemini_result = review_with_gemini(order, GCP_API_KEY, system_prompt=system_prompt)
        # reason 統一格式：AI評估：<Gemini回傳內容>'
        ai_reason = gemini_result.get('reason', '')
        if gemini_result.get('approved', True):
            result = {
                'order': order,
                'status': 'approved',
                'reason': f"AI評估通過：{ai_reason}"
            }
        else:
            result = {
                'order': order,
                'status': 'rejected',
                'reason': f"AI評估拒絕：{ai_reason}"
            }
        print(f"[DEBUG] Gemini result: {result}")
        producer.send(REVIEWED_TOPIC, result)
        time.sleep(1)

if __name__ == '__main__':
    main() 