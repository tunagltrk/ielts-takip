#!/usr/bin/env python3
"""
Bilkent IELTS kayıt takip botu (bulut versiyonu, GitHub Actions'ta çalışır).
Her 20 saniyede 6 oturumu kontrol eder; biri açılınca Telegram'dan telefona mesaj atar.
Bir çalışma ~55 dakika sürer; GitHub her saat yenisini başlatır.
Her gün 09:00 ve 21:00'de "bot çalışıyor" kontrol mesajı atar.
"""

import json
import os
import random
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

INTERVAL = 20               # saniye
RUN_MINUTES = 55            # tek çalışmanın süresi
KONTROL_SAATLERI = (9, 21)  # kontrol mesajı saatleri (Türkiye saati)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID") or "1812046015,5897839750"

PRODUCT_ID = "aa1ac5a7-f66f-45b8-a919-059501c5d35b"
SESSIONS = {
    "7 Kasım Cmt 09:00": "bd379898-d71f-42d2-b095-a6ffee3b8854",
    "7 Kasım Cmt 13:00": "a439b170-a001-4f0f-a117-53b66e79d9f4",
    "7 Kasım Cmt 17:00": "cb51fc22-1725-4d43-aa0d-7a50167b0cae",
    "8 Kasım Paz 09:00": "da8bce5c-3c37-483b-85d9-b38da9eb1b9a",
    "8 Kasım Paz 13:00": "48ec78ec-df26-47de-acb4-ff7237627bb2",
    "8 Kasım Paz 17:00": "b85eaa5f-0419-47a0-bd43-6acb49faa03b",
}

API = "https://api.bxsearch.prod.ielts.com/v1/sessions/private"
PAGE = "https://bxsearch.ielts.idp.com/pvs/session/{sid}/product/" + PRODUCT_ID
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://bxsearch.ielts.idp.com",
    "Referer": "https://bxsearch.ielts.idp.com/",
}
TR = timezone(timedelta(hours=3))


def now():
    return datetime.now(TR).strftime("%H:%M:%S")


def check(sid):
    q = urllib.parse.urlencode({"isPrivate": "true", "productId": PRODUCT_ID, "sessionId": sid})
    req = urllib.request.Request(f"{API}?{q}", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.load(r)
    return data.get("totalCount") or len(data.get("items") or [])


def telegram(text):
    text += "\n\nTuna Beyza'yı çok seviyor ❤️"
    if not (TELEGRAM_TOKEN and TELEGRAM_CHAT_ID):
        print(f"[{now()}] Telegram ayarlı değil, mesaj gönderilemedi: {text}")
        return
    for chat_id in TELEGRAM_CHAT_ID.split(","):
        try:
            body = urllib.parse.urlencode({"chat_id": chat_id.strip(), "text": text}).encode()
            urllib.request.urlopen(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", body, timeout=10)
        except Exception as e:
            print(f"[{now()}] Telegram hatası ({chat_id}): {e}")


def main():
    manual = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
    kontrol_saati = datetime.now(TR).hour in KONTROL_SAATLERI
    end = time.time() + RUN_MINUTES * 60
    notified = set()
    errors = 0
    first_round = True

    print(f"[{now()}] Bot başladı.")
    while time.time() < end:
        status = []
        for name, sid in SESSIONS.items():
            try:
                count = check(sid)
                status.append(f"{name}: {'AÇIK' if count > 0 else 'kapalı'}")
                if count > 0 and sid not in notified:
                    for _ in range(3):  # kaçırma diye 3 kez
                        telegram(f"🚨 IELTS KAYDI AÇILDI!\n{name}\n{PAGE.format(sid=sid)}")
                        time.sleep(1)
                    notified.add(sid)
            except Exception as e:
                errors += 1
                status.append(f"{name}: HATA ({e})")
            time.sleep(0.5)

        print(f"[{now()}] " + " | ".join(status))

        if first_round and (manual or kontrol_saati):
            telegram("😌 PANİK YOK AŞKIM — BOT KONTROL MESAJI\n\n"
                     "✅ Bot çalışıyor, kayıt henüz açılmadı:\n" + "\n".join(status))
        first_round = False

        if errors >= 30:
            telegram("⚠️ IELTS botu IELTS sitesine ulaşamıyor (çok fazla hata). GitHub'daki kayıtlara bak.")
            errors = -10_000  # bir daha uyarma

        time.sleep(INTERVAL + random.uniform(-2, 2))


if __name__ == "__main__":
    main()
