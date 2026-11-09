import os
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# Configuration des deux robots Telegram
EURUSD_TOKEN = os.environ["TELEGRAM_TOKEN_EURUSD"]
XAUUSD_TOKEN = os.environ["TELEGRAM_TOKEN_XAUUSD"]

# Sources officielles d'informations economiques
FED_URL = "https://www.federalreserve.gov/feeds/press_monetary.xml"
ECB_URL = "https://www.ecb.europa.eu/rss/press.html"def get_url(url):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "ForexAnalysisBot/1.0"}
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read()


def get_headlines(url):
    try:
        root = ET.fromstring(get_url(url))
        headlines = []

        for item in root.iter():
            if item.tag.split("}")[-1] in ("item", "entry"):
                for child in item:
                    if child.tag.split("}")[-1] == "title":
                        title = "".join(child.itertext()).strip()
                        if title:
                            headlines.append(title)
                        break

        return headlines[:8]

    except Exception as error:
        print("Erreur de lecture des actualites :", error)
        return []def analyze_market(fed_news, ecb_news):
    fed_text = " ".join(fed_news).lower()
    ecb_text = " ".join(ecb_news).lower()

    usd_score = 0
    eur_score = 0

    hawkish_words = [
        "hawkish", "rate hike", "higher interest rates",
        "monetary tightening"
    ]

    dovish_words = [
        "dovish", "rate cut", "lower interest rates",
        "monetary easing"
    ]

    for word in hawkish_words:
        usd_score += fed_text.count(word)
        eur_score += ecb_text.count(word)

    for word in dovish_words:
        usd_score -= fed_text.count(word)
        eur_score -= ecb_text.count(word)

    eurusd_score = eur_score - usd_score
    gold_score = -usd_score

    def bias(score):
        if score >= 2:
            return "HAUSSIER"
        elif score <= -2:
            return "BAISSIER"
        return "NEUTRE / INCERTAIN"

    return bias(eurusd_score), bias(gold_score)def send_telegram(token, message):
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    request = urllib.request.Request(url)

    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.loads(response.read())

    if not data.get("ok"):
        raise RuntimeError("Erreur Telegram")

    chat_ids = set()

    for update in data.get("result", []):
        msg = update.get("message", {})
        chat = msg.get("chat", {})

        if chat.get("id"):
            chat_ids.add(chat["id"])

    if not chat_ids:
        raise RuntimeError(
            "Aucun destinataire. Envoyez /start au bot."
        )

    send_url = f"https://api.telegram.org/bot{token}/sendMessage"

    for chat_id in chat_ids:
        payload = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": message
        }).encode()

        req = urllib.request.Request(
            send_url,
            data=payload
        )

        with urllib.request.urlopen(req, timeout=20) as response:
            result = json.loads(response.read())

        if not result.get("ok"):
            raise RuntimeError("Envoi Telegram echoue")def main():
    date = datetime.now(timezone.utc).strftime("%d/%m/%Y")

    fed_news = get_headlines(FED_URL)
    ecb_news = get_headlines(ECB_URL)

    eurusd_bias, gold_bias = analyze_market(
        fed_news,
        ecb_news
    )

    fed_list = "\n".join(
        [f"- {title}" for title in fed_news]
    ) or "Aucune actualite disponible."

    ecb_list = "\n".join(
        [f"- {title}" for title in ecb_news]
    ) or "Aucune actualite disponible."

    eurusd_message = (
        f"📊 BRIEFING EUR/USD\n"
        f"Date : {date}\n\n"
        f"Biais indicatif : {eurusd_bias}\n\n"
        f"Actualites FED :\n{fed_list}\n\n"
        f"Actualites BCE :\n{ecb_list}\n\n"
        "⚠️ Analyse automatique preliminaire. "
        "Confirmez avec le calendrier economique et "
        "l'analyse technique avant toute decision."
    )

    gold_message = (
        f"🥇 BRIEFING XAU/USD\n"
        f"Date : {date}\n\n"
        f"Biais indicatif : {gold_bias}\n\n"
        f"Actualites FED :\n{fed_list}\n\n"
        "⚠️ Analyse automatique preliminaire. "
        "Ce biais ne constitue pas un signal de trading."
    )

    send_telegram(EURUSD_TOKEN, eurusd_message)
    send_telegram(XAUUSD_TOKEN, gold_message)


if __name__ == "__main__":
    main()
