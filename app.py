from flask import Flask, request, jsonify
import subprocess
import os
import requests

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")  # من إعدادات Render
CHAT_ID = os.environ.get("CHAT_ID")                # رقم الشات أو القناة

@app.route('/')
def index():
    return jsonify({
        "status": "running",
        "message": "Gallery-DL API + Telegram Bot 🚀"
    })

@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    url = data.get('url')

    if not url:
        return jsonify({"error": "Missing URL"}), 400

    # مجلد التحميل المؤقت
    download_dir = "downloads"
    os.makedirs(download_dir, exist_ok=True)

    try:
        # تحميل باستخدام gallery-dl
        subprocess.run(["gallery-dl", "-d", download_dir, url], check=True)

        # إرسال الملفات إلى تلغرام
        sent_files = []
        for root, dirs, files in os.walk(download_dir):
            for file in files:
                file_path = os.path.join(root, file)
                with open(file_path, "rb") as f:
                    resp = requests.post(
                        f"https://api.telegram.org/bot8183373964:AAF3mXql_cmVYdkWSxclE6HkU0xE2wyxy4U/sendPhoto",
                        data={"chat_id": 290202880},
                        files={"photo": f}
                    )
                    if resp.status_code == 200:
                        sent_files.append(file)

        return jsonify({
            "status": "success",
            "url": url,
            "sent": sent_files
        })

    except subprocess.CalledProcessError:
        return jsonify({"status": "failed"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
