from flask import Flask, request, jsonify
import subprocess
import os
import requests

app = Flask(__name__)

# ✅ معلومات البوت
TELEGRAM_BOT_TOKEN = "ضع_توكن_البوت_هنا"
CHAT_ID = "ضع_الشات_ايدي_هنا"

# ✅ كوكيز DeviantArt
COOKIES = [
    {
        "domain": ".deviantart.com",
        "name": "damztoken",
        "value": "1"
    },
    {
        "domain": ".deviantart.com",
        "name": "auth",
        "value": "__c26b59ce699d1c5e04db%3B%22423ac7cd48ed3d89ad4b99d9f5c65ba4%22"
    },
    {
        "domain": ".deviantart.com",
        "name": "userinfo",
        "value": "__8a3904d0ed9bd6b0ee82%3B%7B%22username%22%3A%22noroameel%22%2C%22uniqueid%22%3A%22d23ffeee69f0550070ae6a075879758f%22%2C%22dvs9-1%22%3A1%2C%22ab%22%3A%22tao-NN5-1-a-4%7Ctao-fg0-1-b-6%7Ctao-DZ6-1-d-7%7Ctao-fu0-1-b-1%7Ctao-ad3-1-b-7%7Ctao-ltc-1-b-2%22%7D"
    },
    {
        "domain": ".deviantart.com",
        "name": "auth_secure",
        "value": "__85096a90c64fca1e2c7d%3B%22607ad673222472a10d42fa74f6b8ecb6%22"
    },
]


def write_cookies_file():
    """يحفظ الكوكيز في ملف بصيغة Netscape المفهومة من gallery-dl"""
    cookies_path = "cookies.txt"
    with open(cookies_path, "w", encoding="utf-8") as f:
        f.write("# Netscape HTTP Cookie File\n")
        for c in COOKIES:
            f.write(f"{c['domain']}\tTRUE\t/\tFALSE\t0\t{c['name']}\t{c['value']}\n")
    return cookies_path


def send_to_telegram(file_path):
    """يرسل الصورة إلى تيليجرام"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    with open(file_path, "rb") as f:
        files = {"photo": f}
        data = {"chat_id": CHAT_ID}
        requests.post(url, data=data, files=files)


@app.route('/')
def index():
    return jsonify({"status": "running"})


@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    url = data.get("url")

    if not url:
        return jsonify({"error": "Missing URL"}), 400

    cookies_file = write_cookies_file()
    output_folder = "downloads"
    os.makedirs(output_folder, exist_ok=True)

    try:
        subprocess.run([
            "gallery-dl",
            "--cookies", cookies_file,
            "-d", output_folder,
            url
        ], check=True)

        # 🔹 إرسال الصور بعد التحميل
        sent_count = 0
        for root, _, files in os.walk(output_folder):
            for file in files:
                if file.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
                    file_path = os.path.join(root, file)
                    send_to_telegram(file_path)
                    sent_count += 1

        return jsonify({"status": "done", "sent": sent_count})

    except subprocess.CalledProcessError:
        return jsonify({"status": "failed"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
