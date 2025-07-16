import pandas as pd
import os
import requests

def is_blacklisted_api(name):
    url = "http://blacklist_api:8000/check"
    try:
        resp = requests.get(url, params={"name": name.strip()})
        data = resp.json()
        return data.get("blacklisted", False), data.get("reason", "")
    except Exception as e:
        print(f"Blacklist API error: {e}")
        return False, "查詢失敗"
