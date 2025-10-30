from flask import Flask, request, jsonify
import subprocess, os

app = Flask(__name__)

@app.route("/download", methods=["POST"])
def download():
    data = request.json
    url = data.get("url")
    outdir = data.get("outdir", "downloads")

    if not url:
        return jsonify({"error": "Missing 'url' field"}), 400

    os.makedirs(outdir, exist_ok=True)

    try:
        result = subprocess.run(
            ["gallery-dl", "-d", outdir, url],
            capture_output=True, text=True
        )
        return jsonify({
            "status": "ok" if result.returncode == 0 else "error",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "output_dir": os.path.abspath(outdir)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
