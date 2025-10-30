from flask import Flask, request, jsonify
import subprocess
import os

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"status": "ok", "message": "API is working!"})

@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    url = data.get("url")

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        # حفظ الصور داخل مجلد downloads
        subprocess.run(["gallery-dl", "-d", "downloads", url], check=True)
        return jsonify({"status": "success", "message": f"Downloaded from {url}"})
    except subprocess.CalledProcessError:
        return jsonify({"status": "error", "message": "Download failed"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
