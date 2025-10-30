from flask import Flask, request, jsonify
import subprocess
import os

app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({
        "status": "running",
        "message": "Gallery-DL API is live 🚀"
    })

@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    url = data.get('url')

    if not url:
        return jsonify({"error": "Missing URL"}), 400

    try:
        subprocess.run(["gallery-dl", "-d", "downloads", url], check=True)
        return jsonify({"status": "success", "url": url})
    except subprocess.CalledProcessError:
        return jsonify({"status": "failed"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

