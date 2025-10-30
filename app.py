from flask import Flask, request, jsonify
import subprocess
import os
import glob
import requests

app = Flask(__name__)

# ✨ غيّري هذه القيم إلى معلوماتك ✨
BOT_TOKEN = "8183373964:AAF3mXql_cmVYdkWSxclE6HkU0xE2wyxy4U"
CHAT_ID = "290202880"

@app.route('/')
def index():
    return jsonify({"status": "running", "message": "Gallery-DL API is live 🚀"})

@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    url = data.get('url')

    if not url:
        return jsonify({"error": "Missing URL"}), 400

    os.makedirs("downloads", exist_ok=True)

    try:
        # تشغيل gallery-dl وحفظ الملفات
        result = subprocess.run(
            ["gallery-dl", "-d", "downloads", url],
            capture_output=True, text=True
        )

        if result.returncode != 0:
            return jsonify({"status": "failed", "error": result.stderr}), 500

        # إيجاد أحدث الملفات
        files = sorted(
            glob.glob("downloads/**/*.*", recursive=True),
            key=os.path.getmtime,
            reverse=True
        )

        if not files:
            return jsonify({"status": "failed", "error": "No files downloaded"}), 500

        # إرسال أول 5 صور فقط حتى لا يطول الإرسال
        sent_files = []
        for img_path in files[:5]:
            with open(img_path, "rb") as f:
                resp = requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                    data={"chat_id": CHAT_ID},
                    files={"photo": f}
                )
            if resp.status_code == 200:
                sent_files.append(os.path.basename(img_path))

        if not sent_files:
            return jsonify({"status": "failed", "error": "No images sent"}), 500

        return jsonify({"status": "success", "sent": sent_files})

    except Exception as e:
        return jsonify({"status": "failed", "error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
