# auto_login_telegram.py
"""
يفتح الموقع، يسجل الدخول، يروح لصفحة SMSCDRStats،
ويعمل refresh كل فترة.
لو لقى أي رسائل جديدة فيها كلمة Telegram أو تلجرام → يفلترها ويستخرج الرقم والكود
ويبعتهم على التليجرام.
"""

import re
import time
import traceback
from datetime import datetime
import requests
from playwright.sync_api import sync_playwright

# ====== إعدادات المستخدم ======
LOGIN_URL = "http://51.89.99.105/NumberPanel/login"
TARGET_URL = "http://51.89.99.105/NumberPanel/agent/SMSCDRStats"
USERNAME = "mazenhassan"
PASSWORD = "mazenhassan861"

BOT_TOKEN = "8212188897:AAGMn8CnyB17e-izeSLG-a4fMHZxMLxsPP4"
CHAT_ID = "-1003098999710"

REFRESH_INTERVAL = 16  # ثواني


# ====== دوال ======
def send_telegram_message(token: str, chat_id: str, text: str) -> bool:
    """يرسل رسالة إلى تليجرام"""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        res = requests.post(url, data={"chat_id": chat_id, "text": text})
        if res.status_code == 200:
            return True
        else:
            print("⚠️ خطأ في إرسال رسالة:", res.status_code, res.text)
            return False
    except Exception as e:
        print("⚠️ خطأ إرسال لتليجرام:", e)
        return False


def parse_math_question(text: str):
    """يحاول يحل سؤال حسابي بسيط موجود في نص الصفحة"""
    m = re.search(r'(-?\d+)\s*([+\-*/x×])\s*(-?\d+)', text)
    if not m:
        return None
    try:
        a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
        if op in ("x", "×"):
            op = "*"
        if op == "+":
            return str(a + b)
        if op == "-":
            return str(a - b)
        if op == "*":
            return str(a * b)
        if op == "/" and b != 0:
            return str(a // b) if a % b == 0 else str(a / b)
    except:
        return None
    return None


# ====== تشغيل ======
def main():
    try:
        print("🚀 بدء التشغيل...")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # --- تسجيل الدخول ---
            print("🔗 فتح صفحة الدخول...")
            page.goto(LOGIN_URL, timeout=60000)

            page.fill("input[name='username']", USERNAME)
            page.fill("input[type='password']", PASSWORD)

            # حل السؤال الحسابي
            body_text = page.content()
            ans = parse_math_question(body_text)
            if ans:
                print(f"🧮 تم إيجاد سؤال حسابي → النتيجة: {ans}")
                for selector in [
                    "input[name='answer']",
                    "input[placeholder*='answer' i]",
                    "input[id*='answer' i]",
                    "input[name*='result' i]",
                    "input[type='text']",
                ]:
                    try:
                        if page.locator(selector).count() > 0:
                            page.fill(selector, ans)
                            print("✅ أدخلت الإجابة الحسابية.")
                            break
                    except:
                        continue

            # الضغط على زر login
            try:
                page.locator("button:has-text('Login'), button:has-text('login')").click(timeout=5000)
                print("✅ ضغطت زر Login.")
            except:
                print("❗ زر login مش موجود")
                return

            time.sleep(4)
            page.goto(TARGET_URL, timeout=60000)
            print("📍 العنوان الحالي:", page.url)

            # --- مراقبة الصفحة ---
            print("🔔 وضع المراقبة شغال...")
            last_page = ""

            while True:
                time.sleep(REFRESH_INTERVAL)
                page.reload()
                time.sleep(1)

                page_text = page.content()

                if page_text != last_page:
                    new_lines = [l for l in page_text.splitlines() if l not in last_page.splitlines()]
                    telegram_lines = [l for l in new_lines if re.search(r"telegram|تلجرام", l, re.IGNORECASE)]
                    if telegram_lines:
                        for line in telegram_lines:
                            phone_match = re.search(r"\b\d{10,15}\b", line)
                            phone = phone_match.group(0) if phone_match else "غير معروف"

                            code_match = re.search(r"Telegram code\s+(\d+)", line, re.IGNORECASE)
                            code = code_match.group(1) if code_match else "غير معروف"

                            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            msg = f"📩 رسالة جديدة ({ts})\n📲 رقم: {phone}\n🔑 كود: {code}"
                            send_telegram_message(BOT_TOKEN, CHAT_ID, msg)
                            print("✅ أرسلت الرقم والكود لتليجرام.")
                    else:
                        print("ℹ️ فيه تحديث بس مفيهوش Telegram.")
                    last_page = page_text
                else:
                    print("ℹ️ لا جديد.")

    except KeyboardInterrupt:
        print("✋ تم إيقاف البرنامج يدويًا.")
    except Exception as e:
        print("⚠️ خطأ:", e)
        traceback.print_exc()


if __name__ == "__main__":
    main()
