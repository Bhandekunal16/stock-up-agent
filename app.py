from flask import Flask, jsonify
from flask_cors import CORS
import subprocess
import os

app = Flask(__name__)
CORS(
    app,
    origins=[
        "http://0.0.0.0:8003",
        "http://147.224.251.137:8003",
    ],
)


@app.route("/api/portfolio/signals", methods=["GET"])
def portfolio_signals():
    try:
        result = subprocess.run(
            ["bash", "runner.sh"],
            capture_output=True,
            text=True,
            timeout=120,
            env=os.environ.copy(),
        )

        return jsonify(
            {
                "success": result.returncode == 0,
                "exitCode": result.returncode,
                "output": result.stdout.strip(),
                "error": result.stderr.strip(),
            }
        ), (200 if result.returncode == 0 else 500)

    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "message": "Script execution timed out"}), 504

    except Exception:
        return (
            jsonify(
                {"success": False, "message": "Failed to execute portfolio signals"}
            ),
            500,
        )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5001,
        debug=False,
    )
