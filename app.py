from flask import Flask, request, jsonify
import subprocess
import os

app = Flask(__name__)

# 🔹 الكوكيز الخاصة بـ DeviantArt
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


@app.route('/')
def index():
    return jsonify({
        "status": "running",
        "message": "Gallery-DL API with cookies is live 🚀"
    })


@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    url = data.get('url')

    if not url:
        return jsonify({"error": "Missing URL"}), 400

    # كتابة ملف الكوكيز قبل التحميل
    cookies_file = write_cookies_file()

    try:
        subprocess.run([
            "gallery-dl",
            "--cookies", cookies_file,
            "-d", "downloads",
            url
        ], check=True)

        return jsonify({"status": "success", "url": url})
    except subprocess.CalledProcessError:
        return jsonify({"status": "failed"}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
