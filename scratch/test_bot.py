import requests
import os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("TELEGRAM_BOT_TOKEN")

print(f"Testing token: {token[:10]}...")
try:
    print("Calling getMe...")
    resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
    print(f"Status Code: {resp.status_code}")
    print(f"Response: {resp.text}")
    
    print("Calling getUpdates...")
    r_upd = requests.get(
        f"https://api.telegram.org/bot{token}/getUpdates?limit=1&offset=-1",
        timeout=10
    )
    print(f"Status Code: {r_upd.status_code}")
    print(f"Response: {r_upd.text}")
except Exception as e:
    print(f"Error: {e}")
