from flask import Flask, render_template, send_from_directory  # IMPORTI
import os

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/data/nigeria")
def nigeria_geojson():
    # Vraća tvoj nigeria.json
    return send_from_directory(STATIC_DIR, "nigeria.json", mimetype="application/json")


if __name__ == "__main__":
    app.run(debug=True)