# app.py
from flask import Flask, request, jsonify
import os, subprocess, json, time, glob
import requests
from pathlib import Path

app = Flask(__name__)

# ----- إعدادات من متغيرات البيئة -----
BOT_TOKEN = os.environ.get("8183373964:AAF3mXql_cmVYdkWSxclE6HkU0xE2wyxy4U")        # ضع توكن البوت في Secrets / Env
CHAT_ID = os.environ.get("290202880")            # ضع Chat ID في Secrets / Env
DELETE_AFTER_SEND = os.environ.get("DELETE_AFTER_SEND", "true").lower() in ("1","true","yes")

# محتوى الكوكيز: إما من متغيرات البيئة أو من ملفات موجودة في الريبو
COOKIES_TWITTER_ENV = os.environ.get("COOKIES_TWITTER")          # محتوى ملف netscape كَسلسلة نصية
COOKIES_DEVIANTART_ENV = os.environ.get("COOKIES_DEVIANTART")

# أسماء الملفات المستخدمة محلياً
COOKIES_TWITTER_FILE = "cookies-twitter.txt"
COOKIES_DEVIANTART_FILE = "cookies-deviantart.txt"
GDL_CONF_FILE = "gallery-dl.conf"

# مجلد التنزيل
OUTPUT_DIR = "downloads"

# ----- وظائف مساعدة -----
def ensure_cookies_files():
    """
    يكتب ملفات الكوكيز من متغيرات البيئة إذا لم تكن موجودة.
    إذا لم تتوفر متغيرات البيئة لكن توجد الملفات في الريبو، نتركها كما هي.
    """
    # تويتر
    if COOKIES_TWITTER_ENV:
        with open(COOKIES_TWITTER_FILE, "w", encoding="utf-8") as f:
            f.write(COOKIES_TWITTER_ENV)
        print(f"[setup] wrote {COOKIES_TWITTER_FILE} from env")
    else:
        if Path(COOKIES_TWITTER_FILE).exists():
            print(f"[setup] {COOKIES_TWITTER_FILE} exists in repo — using it")
        else:
            print(f"[setup] warning: {COOKIES_TWITTER_FILE} not found and COOKIES_TWITTER env missing")

    # ديفاينت آرت
    if COOKIES_DEVIANTART_ENV:
        with open(COOKIES_DEVIANTART_FILE, "w", encoding="utf-8") as f:
            f.write(COOKIES_DEVIANTART_ENV)
        print(f"[setup] wrote {COOKIES_DEVIANTART_FILE} from env")
    else:
        if Path(COOKIES_DEVIANTART_FILE).exists():
            print(f"[setup] {COOKIES_DEVIANTART_FILE} exists in repo — using it")
        else:
            print(f"[setup] warning: {COOKIES_DEVIANTART_FILE} not found and COOKIES_DEVIANTART env missing")

def write_gallery_dl_conf():
    """
    يكتب ملف gallery-dl.conf بسيط يُخبر gallery-dl أي ملف كوكيز يستعمل لكل موقع.
    """
    conf = {
        "extractor": {
            "base-directory": OUTPUT_DIR,
            "twitter": {"cookies": COOKIES_TWITTER_FILE},
            "deviantart": {"cookies": COOKIES_DEVIANTART_FILE}
        }
    }
    with open(GDL_CONF_FILE, "w", encoding="utf-8") as f:
        json.dump(conf, f, indent=2)
    print(f"[setup] wrote {GDL_CONF_FILE}")

def list_files_recursive(folder):
    p = Path(folder)
    if not p.exists():
        return []
    return [str(x) for x in p.rglob('*') if x.is_file()]

def send_media_group(bot_token, chat_id, file_paths, timeout=120):
    """
    يرسل دفعة صور (1..10) عبر sendMediaGroup.
    file_paths: قائمة مسارات كاملة للصور (<=10)
    """
    assert 1 <= len(file_paths) <= 10
    media = []
    files = {}
    for p in file_paths:
        name = os.path.basename(p)
        media.append({"type": "photo", "media": f"attach://{name}"})
        files[name] = open(p, "rb")

    payload = {"chat_id": chat_id, "media": json.dumps(media)}
    url = f"https://api.telegram.org/bot{bot_token}/sendMediaGroup"
    try:
        resp = requests.post(url, data=payload, files=files, timeout=timeout)
        for fh in files.values():
            fh.close()
        if resp.status_code != 200:
            return False, resp.status_code, resp.text
        return True, resp.status_code, resp.json()
    except Exception as e:
        for fh in files.values():
            try:
                fh.close()
            except:
                pass
        return False, None, str(e)

# ----- تهيئة الملفات عند بدء التشغيل -----
ensure_cookies_files()
write_gallery_dl_conf()
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

if not BOT_TOKEN or not CHAT_ID:
    print("[warning] BOT_TOKEN or CHAT_ID not set in environment! Set them in Render/GitHub Secrets before deploying.")

# ----- Routes -----
@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "running", "message": "gallery-dl + cookies + telegram (batched)"})


@app.route("/download", methods=["POST"])
def download():
    """
    تتوقع JSON body: { "url": "..." }
    ستقوم بتحميل الرابط عبر gallery-dl ثم إرسال الصور الجديدة فقط إلى تيليجرام بدفعات 10.
    """
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error":"missing json body"}), 400
    url = data.get("url")
    if not url:
        return jsonify({"error":"missing url in body"}), 400

    # سجل الملفات قبل التحميل
    before = set(list_files_recursive(OUTPUT_DIR))

    # شغّل gallery-dl : لن نمرر --cookies لأننا اعتمدنا gallery-dl.conf
    try:
        proc = subprocess.run(["gallery-dl", "-d", OUTPUT_DIR, url],
                              capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired as e:
        return jsonify({"status":"failed","error":"gallery-dl timeout","detail":str(e)}), 500
    except FileNotFoundError:
        return jsonify({"status":"failed","error":"gallery-dl not found. install gallery-dl in the runtime."}), 500

    if proc.returncode != 0:
        # إرجاع stdout/stderr لمساعدتك في تحليل المشكلة (مثل AuthRequired)
        return jsonify({
            "status":"failed",
            "error":"gallery-dl returned non-zero",
            "stdout": proc.stdout,
            "stderr": proc.stderr
        }), 500

    # جمع الملفات الجديدة فقط
    after = set(list_files_recursive(OUTPUT_DIR))
    new_files = sorted(list(after - before))

    # ترشيح الصور
    images = [p for p in new_files if p.lower().endswith((".jpg",".jpeg",".png",".webp",".gif"))]
    # ترتيب حسب تاريخ التعديل (قد يساعد في إرسال الصور بترتيب)
    images.sort(key=lambda p: os.path.getmtime(p))

    if not images:
        return jsonify({"status":"no_images", "count": 0, "stdout": proc.stdout}), 200

    # إرسال بالدفعات (10 صور)
    total_sent = 0
    errors = []
    for i in range(0, len(images), 10):
        batch = images[i:i+10]
        ok, code, resp = send_media_group(BOT_TOKEN, CHAT_ID, batch)
        if not ok:
            errors.append({
                "batch": [os.path.basename(x) for x in batch],
                "http_code": code,
                "error": resp
            })
        else:
            total_sent += len(batch)
        # تأخير بسيط بين الدفعات لتقليل throttle
        time.sleep(1.5)

    # حذف الصور بعد الإرسال (اختياري)
    if DELETE_AFTER_SEND:
        for p in images:
            try:
                os.remove(p)
            except Exception:
                pass

    return jsonify({
        "status":"done",
        "total_found": len(new_files),
        "images_sent": total_sent,
        "errors": errors,
        "gallery_dl_stdout": proc.stdout
    }), 200

# ----- تشغيل التطبيق -----
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # on Render the web service binds to $PORT
    app.run(host="0.0.0.0", port=port)
