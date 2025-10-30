# app.py
from flask import Flask, request, jsonify
import subprocess, os, glob, json, time, tempfile
import requests

app = Flask(__name__)

# --- إعدادات: احفظ التوكن و Chat ID كمتغيرات بيئية في Render أو النظام ---
BOT_TOKEN = os.environ.get("8183373964:AAF3mXql_cmVYdkWSxclE6HkU0xE2wyxy4U")       # مثال: "123456789:AA..."
CHAT_ID = os.environ.get("290202880")           # مثال: "987654321"
DELETE_AFTER_SEND = os.environ.get("DELETE_AFTER_SEND", "true").lower() in ("1","true","yes")

if not BOT_TOKEN or not CHAT_ID:
    print("تحذير: BOT_TOKEN و CHAT_ID غير معرفين في متغيرات البيئة. ضعهم قبل التشغيل.")

# --- الكوكيز المجمّعة (Twitter + DeviantArt) كما أرسلتها ---
COOKIES = [
    # ---- تويتر / x.com ----
    {"domain": ".x.com", "name": "auth_token", "value": "f42f94e1d2e326680d013742f0a8b0010ffe4d0b"},
    {"domain": ".x.com", "name": "_ga_RJGMY4G45L", "value": "GS2.1.s1761430954$o2$g1$t1761430998$j16$l0$h0"},
    {"domain": ".x.com", "name": "guest_id", "value": "v1%3A176140423621517786"},
    {"domain": ".x.com", "name": "_ga", "value": "GA1.1.332531363.1761162563"},
    {"domain": ".x.com", "name": "twid", "value": "u%3D1694211685"},
    {"domain": "x.com", "name": "g_state", "value": "{\"i_l\":0,\"i_ll\":1761404242153}"},
    {"domain": "x.com", "name": "lang", "value": "en"},
    {"domain": ".x.com", "name": "des_opt_in", "value": "Y"},
    {"domain": ".x.com", "name": "__cf_bm", "value": "HSQ9VvfqQnJiAw9TTSc4MxnLlmnJOvWCzXa9xmXjbu4-1761868015.987975-1.0.1.1-Mv8PKZOahnh1tuBYFiLS0StvbZV48xgxGrfD0lmsDfICjpZbJhj0hMQro5MmX1s7Ia_h6.9KR5jpQKsbuId4y.ajnBCqD2UDuK7O5Zt5teMBpE7u_p1hZepfi4949wIW"},
    {"domain": ".x.com", "name": "__cuid", "value": "8987633996de41e59a0ee1d49bdd1ff7"},
    {"domain": ".x.com", "name": "ct0", "value": "deb28a1225ed4f9e62ac53aae1484dafcd0aa5b758c3c51c9a1c71f93bd00d368fde8c71bf3012c1dbd9307c481a7a3116abb8522a87ad2c0477fda65214ceddd3d8ab3d8f746a82a92f5bedc2a6ed6a"},
    {"domain": ".x.com", "name": "guest_id_ads", "value": "v1%3A176140423621517786"},
    {"domain": ".x.com", "name": "guest_id_marketing", "value": "v1%3A176140423621517786"},
    {"domain": ".x.com", "name": "kdt", "value": "qxjO4urNaS8zH9rVCAXht1cZQ8JJFFXxAA5I2aIJ"},
    {"domain": ".x.com", "name": "personalization_id", "value": "\"v1_Gsu+AzoOtmotbapT/dJgRg==\""},

    # ---- DeviantArt ----
    {"domain": ".deviantart.com", "name": "damztoken", "value": "1"},
    {"domain": ".deviantart.com", "name": "auth", "value": "__430169dae2ae3084eef8%3B%22ace72d2f377b4fd2772f1a60144a4002%22"},
    {"domain": ".deviantart.com", "name": "userinfo", "value": "__8a3904d0ed9bd6b0ee82%3B%7B%22username%22%3A%22noroameel%22%2C%22uniqueid%22%3A%22d23ffeee69f0550070ae6a075879758f%22%2C%22dvs9-1%22%3A1%2C%22ab%22%3A%22tao-NN5-1-a-4%7Ctao-fg0-1-b-6%7Ctao-DZ6-1-d-7%7Ctao-fu0-1-b-1%7Ctao-ad3-1-b-7%7Ctao-ltc-1-b-2%22%7D"},
    {"domain": ".www.deviantart.com", "name": "__stripe_mid", "value": "6111769f-b320-4dd3-a506-2b9c2061c74eacf485"},
    {"domain": ".deviantart.com", "name": "auth_secure", "value": "__85096a90c64fca1e2c7d%3B%22607ad673222472a10d42fa74f6b8ecb6%22"},
    {"domain": "www.deviantart.com", "name": "g_state", "value": "{\"i_l\":0,\"i_ll\":1761698788592}"},
    {"domain": ".deviantart.com", "name": "td", "value": "0:1785%3B2:1593%3B3:1125%3B6:1349x679%3B7:1825%3B10:1125%3B11:536%3B12:1905x953%3B13:1833%3B22:600%3B25:1061%3B27:536%3B28:1105%3B31:1125%3B34:274%3B42:226%3B49:468%3B56:750%3B58:477"},
]

# --- helpers ---
def list_files_recursive(folder):
    out = []
    for root, _, files in os.walk(folder):
        for f in files:
            out.append(os.path.join(root, f))
    return out

def send_media_group(bot_token, chat_id, file_paths):
    """
    يرسل مجموعة (حتى 10) صور باستخدام sendMediaGroup.
    file_paths: قائمة مسارات كاملة للملفات (<=10)
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
        r = requests.post(url, data=payload, files=files, timeout=120)
        # إغلاق الملفات
        for fh in files.values():
            fh.close()
        if r.status_code != 200:
            return False, r.text
        return True, r.json()
    except Exception as e:
        # إغلاق الملفات في حالة الخطأ
        for fh in files.values():
            try: fh.close()
            except: pass
        return False, str(e)

@app.route("/")
def index():
    return jsonify({"status": "running", "message": "Gallery-dl multi-cookies Telegram API"})

@app.route("/download", methods=["POST"])
def download():
    """
    تتلقى JSON جسده:
    {
      "url": "https://...."
    }
    وتعيد JSON الحالة بعد محاولة التحميل والإرسال.
    """
    data = request.get_json(force=True)
    url = data.get("url")
    if not url:
        return jsonify({"error": "missing url"}), 400

    output_dir = "downloads"
    os.makedirs(output_dir, exist_ok=True)

    # لائحة الملفات قبل التنزيل (حتى نرسل الجديد فقط)
    before = set(list_files_recursive(output_dir))

    cookie_path = None
    try:
        # كتابة ملف كوكيز مؤقت بصيغة Netscape understood by gallery-dl
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tf:
            for c in COOKIES:
                line = f"{c['domain']}\tTRUE\t/\tFALSE\t0\t{c['name']}\t{c['value']}\n"
                tf.write(line)
            cookie_path = tf.name

        # تشغيل gallery-dl (تأكد أن gallery-dl مُثبت في البيئة)
        proc = subprocess.run(
            ["gallery-dl", "--cookies", cookie_path, "-d", output_dir, url],
            capture_output=True, text=True
        )

        if proc.returncode != 0:
            return jsonify({
                "status": "failed",
                "error": "gallery-dl returned non-zero",
                "stdout": proc.stdout,
                "stderr": proc.stderr
            }), 500

        # الملفات بعد التنزيل
        after = set(list_files_recursive(output_dir))
        new_files = sorted(list(after - before))  # فقط الملفات الجديدة

        # ترشيح الصور فقط وبترتيب زمني بسيط
        images = [p for p in new_files if p.lower().endswith((".jpg",".jpeg",".png",".webp",".gif"))]
        images.sort(key=lambda p: os.path.getmtime(p))

        if not images:
            return jsonify({"status": "no_images", "count": 0})

        # إرسال بالدفعات (10 صور لكل دفعة)
        total_sent = 0
        errors = []
        for i in range(0, len(images), 10):
            batch = images[i:i+10]
            ok, resp = send_media_group(BOT_TOKEN, CHAT_ID, batch)
            if not ok:
                errors.append({"batch": [os.path.basename(p) for p in batch], "error": resp})
            else:
                total_sent += len(batch)
            # تأخير بسيط بين الدفعات لتقليل احتمالات throttle
            time.sleep(1.5)

        # حذف الصور الجديدة بعد الإرسال (اختياري حسب DELETE_AFTER_SEND)
        if DELETE_AFTER_SEND:
            for p in images:
                try:
                    os.remove(p)
                except Exception:
                    pass

        return jsonify({
            "status": "done",
            "total_found": len(new_files),
            "images_sent": total_sent,
            "errors": errors
        })

    except Exception as e:
        return jsonify({"status": "failed", "error": str(e)}), 500

    finally:
        if cookie_path and os.path.exists(cookie_path):
            try: os.remove(cookie_path)
            except: pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
