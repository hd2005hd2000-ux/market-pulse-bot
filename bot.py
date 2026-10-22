
import os
import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
CHANNEL = os.environ.get("CHANNEL", "@HadiTradingLive").strip()
MESSAGE_FILE = "telegram_message.json"


def get_json(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "MarketPulseBot/1.0"}
    )
    with urllib.request.urlopen(req, timeout=12) as response:
        return json.loads(response.read().decode("utf-8"))


def telegram(method, data):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body)
    with urllib.request.urlopen(req, timeout=20) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("ok"):
        raise RuntimeError(f"Telegram API error: {result}")
    return result["result"]


def price(url, key=None):
    try:
        data = get_json(url)
        value = data
        if key:
            for part in key.split("."):
                value = value[part]
        return value
    except Exception:
        return None


def fmt(value, digits=2):
    if value is None:
        return "غير متاح حالياً"
    try:
        return f"${float(value):,.{digits}f}"
    except (ValueError, TypeError):
        return "غير متاح حالياً"


def load_message_id():
    try:
        with open(MESSAGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("message_id")
    except Exception:
        return None


def save_message_id(message_id):
    with open(MESSAGE_FILE, "w", encoding="utf-8") as f:
        json.dump({"message_id": message_id}, f)


def main():
    if not BOT_TOKEN:
        raise RuntimeError("Missing BOT_TOKEN secret in GitHub Actions.")

    # Gold spot price in USD per troy ounce
    gold = price("https://api.gold-api.com/price/XAU", "price")

    # Official reference exchange rate; not Iraq's parallel-market rate
    usd_iqd = price(
        "https://open.er-api.com/v6/latest/USD",
        "rates.IQD"
    )

    # Crypto prices from Binance public ticker API
    symbols = {
        "Bitcoin": "BTCUSDT",
        "Ethereum": "ETHUSDT",
        "BNB": "BNBUSDT",
        "Solana": "SOLUSDT",
        "XRP": "XRPUSDT",
        "Dogecoin": "DOGEUSDT",
    }

    crypto_lines = []
    for name, symbol in symbols.items():
        value = price(
            "https://api.binance.com/api/v3/ticker/price?symbol=" + symbol,
            "price"
        )
        crypto_lines.append(f"• {name}: {fmt(value, 6 if name in ('XRP', 'Dogecoin') else 2)}")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    message = (
        "📊 نبض الأسواق | MARKET PULSE\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"🥇 الذهب XAU/USD: {fmt(gold)} للأونصة\n\n"
        "💵 الدولار مقابل الدينار العراقي:\n"
        f"السعر المرجعي: {fmt(usd_iqd)} دينار/دولار\n"
        "⚠️ هذا سعر مرجعي رسمي، وليس سعر السوق الموازي العراقي.\n\n"
        "₿ العملات الرقمية:\n"
        + "\n".join(crypto_lines)
        + "\n\n"
        "🛢️ النفط | 💱 الفوركس | 📈 الأسهم:\n"
        "الأسعار غير متاحة حالياً من مصدر موثوق مهيأ.\n\n"
        f"🕒 آخر تحديث: {now}\n"
        "المعلومات للتثقيف والمتابعة وليست توصية استثمارية."
    )

    message_id = load_message_id()

    if message_id:
        try:
            telegram("editMessageText", {
                "chat_id": CHANNEL,
                "message_id": message_id,
                "text": message,
                "disable_web_page_preview": "true"
            })
            print("Existing channel message updated.")
            return
        except Exception as exc:
            print(f"Could not edit previous message: {exc}")

    result = telegram("sendMessage", {
        "chat_id": CHANNEL,
        "text": message,
        "disable_web_page_preview": "true"
    })
    message_id = result["message_id"]
    save_message_id(message_id)
    print(f"Published message {message_id}.")


if __name__ == "__main__":
    main()
