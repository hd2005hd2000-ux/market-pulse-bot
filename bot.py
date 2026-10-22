
import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
CHANNEL = os.environ.get("CHANNEL", "@HadiTradingLive")
INTERVAL = max(10, int(os.environ.get("UPDATE_SECONDS", "10")))

TELEGRAM = "https://api.telegram.org/bot" + BOT_TOKEN
MESSAGE_ID = None

def get_json(url, headers=None):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "MarketPulseBot/1.0",
                 **(headers or {})}
    )
    with urllib.request.urlopen(req, timeout=12) as response:
        return json.loads(response.read().decode("utf-8"))

def telegram(method, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        TELEGRAM + "/" + method,
        data=data,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("ok"):
        raise RuntimeError("Telegram API returned an error")
    return result["result"]

def gold_price():
    data = get_json("https://api.gold-api.com/price/XAU")
    price = data.get("price")
    if price is None:
        raise ValueError("Gold price unavailable")
    return float(price)

def crypto_price(symbol):
    url = (
        "https://api.binance.com/api/v3/ticker/price?symbol="
        + urllib.parse.quote(symbol)
    )
    data = get_json(url)
    return float(data["price"])

def usd_iqd_reference():
    data = get_json("https://open.er-api.com/v6/latest/USD")
    rate = data.get("rates", {}).get("IQD")
    if rate is None:
        raise ValueError("USD/IQD unavailable")
    return float(rate)

def price_or_unavailable(fn, fmt):
    try:
        return fmt(fn())
    except Exception:
        return "غير متاح حالياً"

def build_message():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    gold = price_or_unavailable(
        gold_price, lambda p: f"${p:,.2f} للأونصة"
    )
    usd = price_or_unavailable(
        usd_iqd_reference, lambda p: f"{p:,.2f} دينار/دولار"
    )

    coins = [
        ("BTCUSDT", "Bitcoin"),
        ("ETHUSDT", "Ethereum"),
        ("BNBUSDT", "BNB"),
        ("SOLUSDT", "Solana"),
        ("XRPUSDT", "XRP"),
        ("DOGEUSDT", "Dogecoin"),
    ]

    lines = [
        "📊 نبض الأسواق | MARKET PULSE",
        "━━━━━━━━━━━━━━━━━━",
        "🥇 الذهب XAU/USD: " + gold,
        "",
        "💵 الدولار مقابل الدينار العراقي",
        "السعر المرجعي: " + usd,
        "⚠️ سعر الصرف المرجعي ليس سعر السوق الموازي العراقي.",
        "",
        "₿ العملات الرقمية",
    ]

    for symbol, name in coins:
        price = price_or_unavailable(
            lambda s=symbol: crypto_price(s),
            lambda p: f"${p:,.8f}".rstrip("0").rstrip(".")
        )
        lines.append(f"{name}: {price}")

    lines.extend([
        "",
        "💱 الفوركس والنفط والأسهم: تحتاج إلى مصدر بيانات يدعم الرموز المطلوبة.",
        "🕒 وقت بناء التحديث: " + now,
        "تُحدّث الرسالة حسب توفر المصادر وحدودها.",
        "المعلومات ليست توصية استثمارية."
    ])
    return "\n".join(lines)

def publish_or_edit(text):
    global MESSAGE_ID

    if MESSAGE_ID is None:
        result = telegram("sendMessage", {
            "chat_id": CHANNEL,
            "text": text,
            "disable_web_page_preview": True
        })
        MESSAGE_ID = result["message_id"]
    else:
        try:
            telegram("editMessageText", {
                "chat_id": CHANNEL,
                "message_id": MESSAGE_ID,
                "text": text,
                "disable_web_page_preview": True
            })
        except Exception as exc:
            # If Telegram says the text is unchanged, retain the message.
            if "message is not modified" not in str(exc).lower():
                raise

def main():
    if not BOT_TOKEN:
        raise RuntimeError("Set BOT_TOKEN in hosting environment variables")

    while True:
        try:
            publish_or_edit(build_message())
            print("Market update completed")
        except Exception as exc:
            print("Update failed:", str(exc)[:300])

        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
