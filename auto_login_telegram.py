# auto_login_telegram.py
"""
نسخة محدثة تعمل على Render بدون الحاجة لتثبيت chromium يدويًا.
"""

import re
import time
import sys
import traceback
from datetime import datetime
import requests

# ====== إعدادات المستخدم ======
LOGIN_URL = "http://51.89.99.105/NumberPanel/login"
TARGET_URL = "http://51.89.99.105/NumberPanel/agent/SMSCDRStats"
USERNAME = "mazenhassan"
PASSWORD = "mazenhassan861"

BOT_TOKEN = "8212188897:AAGMn8CnyB17e-izeSLG-a4fMHZxMLxsPP4"
CHAT_ID = "-1003098999710"

REFRESH_INTERVAL = 16  # ثواني

# ====== المكتبات ======
try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
except Exception:
    print("❌ لازم تثبت selenium و undetected-chromedriver")
    sys.exit(1)


# ====== الدوال ======
def send_telegram_message(token: str, chat_id: str, text: str) -> bool:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        res = requests.post(url, data={"chat_id": chat_id, "text": text})
        return res.status_code == 200
    except Exception as e:
        print("⚠️ خطأ إرسال لتليجرام:", e)
        return False


def parse_math_question(text: str):
    """حل سؤال حسابي بسيط"""
    m = re.search(r'(-?\d+)\s*([+\-*/x×])\s*(-?\d+)', text)
    if not m:
        return None
    try:
        a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
        if op in ("x", "×"):
            op = "*"
        return str(eval(f"{a}{op}{b}"))
    except:
        return None


def setup_driver():
    """إعداد المتصفح تلقائيًا حتى لو Chromium مش مثبت"""
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    print("🚀 تشغيل متصفح Chromium مدمج...")
    driver = uc.Chrome(options=options)
    return driver


# ====== التشغيل ======
def main():
    while True:
        try:
            driver = setup_driver()
            wait = WebDriverWait(driver, 12)

            # --- تسجيل الدخول ---
            print("🔗 فتح صفحة الدخول...")
            driver.get(LOGIN_URL)

            username_elem = wait.until(EC.presence_of_element_located((By.NAME, "username")))
            password_elem = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='password']")))
            username_elem.send_keys(USERNAME)
            password_elem.send_keys(PASSWORD)

            # حل السؤال الحسابي
            body_text = driver.find_element(By.TAG_NAME, "body").text
            ans = parse_math_question(body_text)
            if ans:
                print("🧮 النتيجة:", ans)
                try:
                    answer_elem = driver.find_element(By.XPATH, "//input[@type='text']")
                    answer_elem.clear()
                    answer_elem.send_keys(ans)
                except:
                    pass

            # زر login
            try:
                btn = driver.find_element(By.XPATH, "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'login')]")
                btn.click()
                print("✅ ضغطت زر Login.")
            except:
                print("❗ زر login مش موجود")
                return

            time.sleep(4)
            driver.get(TARGET_URL)
            time.sleep(2)
            print("📍 العنوان الحالي:", driver.current_url)

            # --- مراقبة الصفحة ---
            print("🔔 وضع المراقبة شغال...")
            last_page = ""
            while True:
                time.sleep(REFRESH_INTERVAL)
                driver.refresh()
                time.sleep(1)

                page_text = driver.find_element(By.TAG_NAME, "body").text
                if page_text != last_page:
                    new_lines = [l for l in page_text.splitlines() if l not in last_page.splitlines()]
                    telegram_lines = [l for l in new_lines if re.search(r"telegram|تلجرام", l, re.IGNORECASE)]

                    if telegram_lines:
                        for line in telegram_lines:
                            phone = re.search(r"\b\d{10,15}\b", line)
                            phone = phone.group(0) if phone else "غير معروف"
                            code = re.search(r"Telegram code\s+(\d+)", line, re.IGNORECASE)
                            code = code.group(1) if code else "غير معروف"
                            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            msg = f"📩 ({ts})\n📲 رقم: {phone}\n🔑 كود: {code}"
                            send_telegram_message(BOT_TOKEN, CHAT_ID, msg)
                            print("✅ أرسلت الرقم والكود لتليجرام.")
                    else:
                        print("ℹ️ مفيش جديد متعلق بـ Telegram.")
                    last_page = page_text
                else:
                    print("ℹ️ لا جديد.")

        except Exception as e:
            print("⚠️ خطأ:", e)
            traceback.print_exc()
            print("🔁 إعادة تشغيل بعد 10 ثواني...")
            time.sleep(10)
        finally:
            try:
                driver.quit()
            except:
                pass


if __name__ == "__main__":
    main()
