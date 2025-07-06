import requests

def send_to_telegram(bot_token: str, chat_id: str, message: str):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {"chat_id": chat_id, "text": message}
    response = requests.post(url, data=data)
    if not response.ok:
        raise Exception(f"Gagal kirim ke Telegram: {response.text}")