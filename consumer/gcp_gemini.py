from google import genai
import os

def review_with_gemini(order, api_key=None, system_prompt=None):
    if api_key is None:
        api_key = os.getenv('GEMINI_API_KEY', '')
    client = genai.Client(api_key=api_key)
    prompt = system_prompt or ""
    user_content = f"訂單資料：{order}"
    contents = [
        {"role": "user", "parts": [{"text": f"{prompt}\n{user_content}"}]}
    ]
    response = client.models.generate_content(
        model="gemini-1.5-pro-latest", contents=contents
    )
    text = response.text
    if text.strip().startswith("通過"):
        return {'approved': True, 'reason': text.strip()}
    else:
        return {'approved': False, 'reason': text.strip()} 