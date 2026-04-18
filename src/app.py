from flask import Flask, render_template, send_from_directory, jsonify
import os
import pyodbc

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")


def get_connection():
    # Konekcija ka tvojoj lokalnoj bazi
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=localhost;"
        "DATABASE=SotexHackathon;"
        "UID=sa;"
        "PWD=SotexSolutions123!;"
        "TrustServerCertificate=yes;"
    )
    return conn


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/data/nigeria")
def nigeria_geojson():
    return send_from_directory(STATIC_DIR, "nigeria.json", mimetype="application/json")


@app.route("/data/trafostanice")
def trafostanice():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        features = []

        # Lista tabela koje želimo da prođemo
        # PAŽNJA: Proveri još jednom da li se tabela zove DistributionSubstation ili DistributionSubstations
        tabele = [
            ("TransmissionStations", "transmission"),
            ("Substations", "substation"),
            ("DistributionSubstation", "distribution")
        ]

        for tabela_ime, tip in tabele:
            # SQL upit za svaku tabelu
            cursor.execute(f"SELECT Name, Latitude, Longitude FROM {tabela_ime}")
            rows = cursor.fetchall()

            for row in rows:
                # PROVERA: Preskačemo stanicu ako su koordinate prazne (NULL u bazi)
                if row[1] is not None and row[2] is not None:
                    try:
                        features.append({
                            "type": "Feature",
                            "geometry": {
                                "type": "Point",
                                # row[2] je Longitude, row[1] je Latitude
                                "coordinates": [float(row[2]), float(row[1])]
                            },
                            "properties": {
                                "naziv": row[0] if row[0] else "Nepoznato",
                                "tip": tip
                            }
                        })
                    except (ValueError, TypeError):
                        # Ako podaci nisu brojevi, samo preskoči taj red
                        continue

        conn.close()
        return jsonify({
            "type": "FeatureCollection",
            "features": features
        })

    except Exception as e:
        # Ako se desi greška (npr. pogrešno ime tabele), ispisaće nam tačno koja
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)