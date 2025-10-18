# auto_login_telegram.py
"""
يفتح الموقع، يسجل الدخول، يروح لصفحة SMSCDRStats،
ويعمل refresh كل فترة.
لو لقى أي رسائل جديدة فيها كلمة Telegram أو تلجرام → يفلترها ويستخرج الرقم والكود
ويبعتهم على التليجرام.
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
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import chromedriver_autoinstaller
except Exception:
    print("❌ لازم تثبت selenium و chromedriver-autoinstaller")
    sys.exit(1)

# ====== دوال ======
def send_telegram_message(token: str, chat_id: str, text: str) -> bool:
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


def setup_driver():
    """إعداد المتصفح بشكل آمن ومتوافق مع Render"""
    chrome_options = Options()

    # تحديد مكان المتصفح على Render
    chrome_options.binary_location = "/usr/bin/chromium"

    # إعدادات التشغيل بدون واجهة
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # تثبيت chromedriver تلقائيًا
    chromedriver_autoinstaller.install()

    return webdriver.Chrome(service=Service(), options=chrome_options)


# ====== التشغيل ======
def main():
    while True:  # إعادة التشغيل التلقائي في حال حدوث أي خطأ
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
                print("🧮 تم إيجاد سؤال حسابي → النتيجة:", ans)
                answer_elem = None
                for xp in [
                    "//input[@name='answer']",
                    "//input[contains(translate(@placeholder,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'answer')]",
                    "//input[contains(translate(@id,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'answer')]",
                    "//input[contains(translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'result')]",
                    "//input[@type='text']"
                ]:
                    try:
                        answer_elem = driver.find_element(By.XPATH, xp)
                        if answer_elem.is_displayed():
                            answer_elem.clear()
                            answer_elem.send_keys(ans)
                            print("✅ أدخلت الإجابة الحسابية.")
                            break
                    except:
                        continue

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
                    # استخرج السطور الجديدة فقط
                    new_lines = [l for l in page_text.splitlines() if l not in last_page.splitlines()]
                    telegram_lines = [l for l in new_lines if re.search(r"telegram|تلجرام", l, re.IGNORECASE)]
                    if telegram_lines:
                        for line in telegram_lines:
                            # 🔍 استخراج الرقم
                            phone_match = re.search(r"\b\d{10,15}\b", line)
                            phone = phone_match.group(0) if phone_match else "غير معروف"

                            # 🔍 استخراج الكود
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

        except Exception as e:
            print("⚠️ خطأ:", e)
            traceback.print_exc()
            print("🔁 إعادة تشغيل خلال 10 ثواني...")
            time.sleep(10)
        finally:
            try:
                driver.quit()
            except:
                pass


if __name__ == "__main__":
    main()
