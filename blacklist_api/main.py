import os
import pandas as pd
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

BLACKLIST_CSV_PATH = os.getenv('BLACKLIST_CSV_PATH', './blacklist.csv')
app = FastAPI()

def load_blacklist():
    try:
        df = pd.read_csv(BLACKLIST_CSV_PATH)
        return set(df['name'].astype(str))
    except Exception:
        return set()

@app.get('/check')
def check_blacklist(name: str = Query(...)):
    import pandas as pd
    df = pd.read_csv(BLACKLIST_CSV_PATH)
    name = name.strip().upper()
    for _, row in df.iterrows():
        name_zh = str(row.get('name_zh', '')).strip().upper()
        name_en = str(row.get('name_en', '')).strip().upper()
        if name == name_zh or name == name_en:
            return JSONResponse({'blacklisted': True, 'reason': row.get('reason', '')})
    return JSONResponse({'blacklisted': False, 'reason': ''}) 