import streamlit as st
from blacklist_utils import is_blacklisted_api
from kafka_utils import send_order
import pandas as pd
import re
import requests
from kafka import KafkaConsumer
import json
import time
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'consumer')))
from gcp_gemini import review_with_gemini

st.title('人壽/健康/醫療保險訂單審核系統')

# Sidebar: GCP Gemini API 連線狀態
with st.sidebar:
    st.header("GCP Gemini API 連線狀態")
    try:
        test_order = {"name": "測試", "income": 10000}
        test_prompt = "請回覆：通過。"
        result = review_with_gemini(test_order, system_prompt=test_prompt)
        if "通過" in result.get("reason", "") or result.get("approved", False):
            st.success("GCP Gemini API 已連線")
        else:
            st.error(f"GCP Gemini API 連線失敗，回傳：{result.get('reason', '')}")
    except Exception as e:
        st.error(f"GCP Gemini API 連線失敗: {e}")

# 只針對人壽/健康/醫療保險
with st.form("order_form"):
    # 一、基本個人資料
    name = st.text_input("姓名", key="name")
    id_number = st.text_input("證件號(身分證)", key="id_number", max_chars=10, help="格式：1個大寫英文字母+9位數字")
    birth = st.date_input("出生日期", key="birth")
    gender = st.selectbox("性別", ["男", "女"], key="gender")
    phone = st.text_input("聯絡電話", key="phone", max_chars=10, help="台灣手機格式 09xxxxxxxx")
    address = st.text_input("聯絡地址", key="address")
    email = st.text_input("電子郵件", key="email")

    # 二、財務與家庭狀況
    job = st.text_input("職業", key="job")
    income = st.number_input("年收入(元)", min_value=0, step=1, key="income")
    marital = st.selectbox("婚姻狀況", ["未婚", "已婚", "離婚", "喪偶"], key="marital")
    family = st.text_area("家庭成員資料 (如：配偶、子女、父母等)", key="family")

    # 三、健康與生活習慣
    height = st.number_input("身高(cm)", min_value=100, max_value=250, step=1, key="height")
    weight = st.number_input("體重(kg)", min_value=30, max_value=200, step=1, key="weight")
    history = st.text_area("既往病史（例如慢性病、重大疾病）", key="history")
    health_status = st.selectbox("目前健康狀況", ["健康", "輕微不適", "需追蹤", "罹患重大疾病"], key="health_status")
    smoke = st.selectbox("是否吸菸", ["否", "是"], key="smoke")
    drink = st.selectbox("是否喝酒", ["否", "是"], key="drink")
    family_history = st.text_area("家族病史 (如：高血壓、糖尿病等)", key="family_history")
    rejected = st.selectbox("是否曾被其他保險公司拒保或加費承保", ["否", "是"], key="rejected")
    medication = st.text_area("目前正在服用的藥物", key="medication")

    # 四、生活活動
    activities = st.multiselect(
        "有在從事的活動（可複選）",
        ["高空彈跳", "潛水", "攀岩", "飛行運動", "機車賽", "登山", "滑雪", "其他"],
        key="activities"
    )
    other_activity = ""
    if "其他" in activities:
        other_activity = st.text_input("請輸入其他活動內容", key="other_activity")

    submitted = st.form_submit_button("送出審核")

def get_review_result(name):
    consumer = KafkaConsumer(
        'order_reviewed',
        bootstrap_servers='kafka:9092',
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        group_id='streamlit-review-group'
    )
    # 輪詢 10 秒內的訊息
    start = time.time()
    for msg in consumer:
        result = msg.value
        if result['order']['name'] == name:
            consumer.close()
            return result
        if time.time() - start > 10:
            break
    consumer.close()
    return None

if submitted:
    # 驗證
    errors = []
    if not name:
        errors.append("姓名為必填")
    if not re.match(r"^[A-Z][0-9]{9}$", id_number):
        errors.append("證件號格式錯誤，需為1個大寫英文字母+9位數字")
    if birth > pd.Timestamp.today().date():
        errors.append("出生日期不可大於今天")
    if not phone or not re.match(r"^09[0-9]{8}$", phone):
        errors.append("聯絡電話格式錯誤，需為台灣手機格式 09xxxxxxxx")
    if not address:
        errors.append("聯絡地址為必填")
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        errors.append("電子郵件格式錯誤")
    if not job:
        errors.append("職業為必填")
    if income <= 0:
        errors.append("年收入需為正整數")
    if not marital:
        errors.append("婚姻狀況為必填")
    if not family:
        errors.append("家庭成員資料為必填")
    if not (100 <= height <= 250):
        errors.append("身高需在100~250之間")
    if not (30 <= weight <= 200):
        errors.append("體重需在30~200之間")
    # 活動欄位處理
    activities_final = [a for a in activities if a != "其他"]
    if "其他" in activities and other_activity:
        activities_final.append(other_activity)

    if errors:
        for err in errors:
            st.error(err)
    else:
        name_clean = name.strip().upper()
        blacklisted, reason = is_blacklisted_api(name_clean)
        if blacklisted:
            st.error(f"黑名單拒絕：{reason}")
        else:
            order = {
                "name": name_clean,
                "id_number": id_number,
                "birth": str(birth),
                "gender": gender,
                "phone": phone,
                "address": address,
                "email": email,
                "job": job,
                "income": income,
                "marital": marital,
                "family": family,
                "height": height,
                "weight": weight,
                "history": history,
                "health_status": health_status,
                "smoke": smoke,
                "drink": drink,
                "family_history": family_history,
                "rejected": rejected,
                "medication": medication,
                "activities": activities_final,
                "insurance_type": "人壽/健康/醫療"
            }
            send_order(order)
            st.info("已送出訂單，請稍候 AI/規則審核結果...")
            # 自動輪詢審核結果
            with st.spinner("自動查詢審核結果中..."):
                result = get_review_result(name_clean)
                if result:
                    # 明確標示來源
                    if result['reason'].startswith('GCP API 審核通過'):
                        st.success(f"AI 風險評估通過：{result['reason']}")
                    elif result['reason'].startswith('GCP API 審核拒絕'):
                        st.error(f"AI 風險評估拒絕：{result['reason']}")
                    elif result['reason'] == '黑名單審核通過':
                        st.success("規則審核通過：黑名單審核通過")
                    elif result['reason'] == '黑名單拒絕':
                        st.error("黑名單拒絕")
                    else:
                        st.info(f"審核結果：{result['status']}，原因：{result['reason']}")
                else:
                    st.info("尚未收到審核結果，請稍候再查詢。") 