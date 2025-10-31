from flask import Flask, request, jsonify
import subprocess
import os
import requests
import glob
import json
import time
import tempfile

app = Flask(__name__)

# إعدادات التيليجرام
BOT_TOKEN = "8183373964:AAF3mXql_cmVYdkWSxclE6HkU0xE2wyxy4U"
CHAT_ID = "290202880"

# الكوكيز المدمجة (من JSON الذي أرسلته)
COOKIES = [
    {"domain": ".deviantart.com", "name": "damztoken", "value": "1"},
    {"domain": ".deviantart.com", "name": "auth", "value": "__c26b59ce699d1c5e04db%3B%22423ac7cd48ed3d89ad4b99d9f5c65ba4%22"},
    {"domain": ".deviantart.com", "name": "userinfo", "value": "__8a3904d0ed9bd6b0ee82%3B%7B%22username%22%3A%22noroameel%22%2C%22uniqueid%22%3A%22d23ffeee69f0550070ae6a075879758f%22%2C%22dvs9-1%22%3A1%2C%22ab%22%3A%22tao-NN5-1-a-4%7Ctao-fg0-1-b-6%7Ctao-DZ6-1-d-7%7Ctao-fu0-1-b-1%7Ctao-ad3-1-b-7%7Ctao-ltc-1-b-2%22%7D"},
    {"domain": ".www.deviantart.com", "name": "__stripe_mid", "value": "6111769f-b320-4dd3-a506-2b9c2061c74eacf485"},
    {"domain": ".deviantart.com", "name": "auth_secure", "value": "__85096a90c64fca1e2c7d%3B%22607ad673222472a10d42fa74f6b8ecb6%22"},
    {"domain": "www.deviantart.com", "name": "g_state", "value": "{\"i_l\":0,\"i_ll\":1761698788592}"},
    {"domain": ".deviantart.com", "name": "td", "value": "0:1785%3B2:1593%3B3:1125%3B6:1349x679%3B7:1753%3B10:1125%3B11:536%3B12:1905x953%3B13:1833%3B27:820%3B28:820%3B31:1125%3B34:274%3B42:226%3B49:428%3B58:308"}
]


@app.route('/')
def index():
    return jsonify({
        "status": "running",
        "message": "Gallery-DL Telegram API is live 🚀"
    })


@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    url = data.get('url')

    if not url:
        return jsonify({"error": "Missing URL"}), 400

    output_dir = "downloads"
    os.makedirs(output_dir, exist_ok=True)

    try:
        # إنشاء ملف كوكيز مؤقت
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            for c in COOKIES:
                line = f"{c['domain']}\tTRUE\t/\tFALSE\t0\t{c['name']}\t{c['value']}\n"
                f.write(line)
            cookie_path = f.name

        # تحميل باستخدام gallery-dl مع الكوكيز
        subprocess.run(
            ["gallery-dl", "--cookies", cookie_path, "-d", output_dir, url],
            check=True
        )

        # جمع الصور
        images = []
        for ext in ["jpg", "jpeg", "png", "webp", "gif"]:
            images.extend(glob.glob(f"{output_dir}/**/*.{ext}", recursive=True))

        if not images:
            return jsonify({"status": "failed", "error": "no images found"}), 500

        # إرسال الصور إلى التيليجرام على دفعات من 10
        for i in range(0, len(images), 10):
            batch = images[i:i + 10]
            media = [{"type": "photo", "media": f"attach://{os.path.basename(img)}"} for img in batch]
            files = {os.path.basename(img): open(img, "rb") for img in batch}

            payload = {
                "chat_id": CHAT_ID,
                "media": json.dumps(media)
            }

            r = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMediaGroup",
                data=payload,
                files=files
            )

            for f in files.values():
                f.close()

            time.sleep(2)

        # حذف الصور بعد الإرسال
        for img in images:
            os.remove(img)

        return jsonify({"status": "success", "count": len(images)})

    except subprocess.CalledProcessError:
        return jsonify({"status": "failed", "error": "gallery-dl error"}), 500
    except Exception as e:
        return jsonify({"status": "failed", "error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
