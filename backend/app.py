# backend/app.py
import os
import time
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

from utils.predict import predict_image
from utils import firestore
from utils.scraper import scrape_plants_for_disease

# ---------------- PATHS ----------------
BASE_DIR = os.path.dirname(__file__)
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend"))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(
    __name__,
    static_folder=FRONTEND_DIR,
    static_url_path=""
)
CORS(app)

# ---------------- FIREBASE INIT ----------------
try:
    firestore.init_firebase(os.path.join(BASE_DIR, "firebase_config.json"))
    print("[INFO] Firebase initialized")
except Exception as e:
    print("[WARN] Firebase init failed:", e)

db = firestore.get_db()

# ---------------- CACHE ----------------
DISEASE_CACHE = {}
CACHE_TTL = 600


def cache_get(q: str):
    entry = DISEASE_CACHE.get(q)
    if not entry:
        return None
    if time.time() - entry["ts"] > CACHE_TTL:
        return None
    return entry


def cache_set(q: str, source: str, plants):
    DISEASE_CACHE[q] = {
        "ts": time.time(),
        "source": source,
        "plants": plants
    }


# ---------------- ROUTES ----------------

@app.route("/")
def index():
    return app.send_static_file("index.html")


# ---------------- GET ALL PLANTS ----------------
@app.route("/plants", methods=["GET"])
def get_plants():
    try:
        plants = firestore.get_all_plants()
        return jsonify({"plants": plants})
    except Exception as e:
        print("[ERROR] get_plants:", e)
        return jsonify({"plants": []})


# ---------------- ADD PLANT ----------------
@app.route("/plants", methods=["POST"])
def add_plant():
    try:
        form = request.form
        image_file = request.files.get("image_file")

        required = ["name", "parts", "uses", "region"]
        missing = [k for k in required if not form.get(k)]
        if missing:
            return jsonify({"success": False, "error": f"Missing fields: {missing}"}), 400

        name = form.get("name").strip().lower()
        region = form.get("region").strip()

        new_parts = [p.strip().lower() for p in form.get("parts").split(",") if p.strip()]
        new_uses = [u.strip().lower() for u in form.get("uses").split(",") if u.strip()]
        new_diseases = [d.strip().lower() for d in form.get("diseases", "").split(",") if d.strip()]

        existing = (
            db.collection("plants")
            .where("name", "==", name)
            .limit(1)
            .get()
        )

        image_url = ""
        if image_file:
            filename = secure_filename(image_file.filename)
            saved_path = os.path.join(
                UPLOAD_DIR, f"plant_{int(time.time())}_{filename}"
            )
            image_file.save(saved_path)
            image_url = request.host_url + "uploads/" + os.path.basename(saved_path)

        if existing:
            doc = existing[0]
            data = doc.to_dict()

            merged_parts = list(set(data.get("parts", []) + new_parts))
            merged_uses = list(set(data.get("uses", []) + new_uses))
            merged_diseases = list(set(data.get("diseases", []) + new_diseases))

            dataset_count = data.get("dataset_count", 0) + 1
            plant_no = data["no"]

            doc.reference.update({
                "parts": merged_parts,
                "uses": merged_uses,
                "diseases": merged_diseases,
                "dataset_count": dataset_count,
                "dataset_ready": dataset_count >= 50,
                "image_url": image_url or data.get("image_url")
            })

        else:
            try:
                total_plants = db.collection("plants").count().get()[0][0].value
            except Exception:
                total_plants = 0

            plant_no = total_plants + 1
            dataset_count = 1

            plant_data = {
                "no": plant_no,
                "name": name,
                "region": region,
                "parts": new_parts,
                "uses": new_uses,
                "diseases": new_diseases,
                "image_url": image_url,
                "dataset_ready": False,
                "dataset_count": dataset_count
            }

            firestore.add_plant(plant_data)

        DISEASE_CACHE.clear()

        THRESHOLD = 50
        print(f"[DATASET] {name} → {dataset_count} / {THRESHOLD} images")

        if dataset_count >= THRESHOLD:
            print(f"[DATASET] {name} → READY ✅ (class_no={plant_no})")

        return jsonify({
            "success": True,
            "name": name,
            "class_no": plant_no,
            "dataset_count": dataset_count
        })

    except Exception as e:
        print("[ERROR] add_plant:", e)
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------- SEARCH BY DISEASE ----------------
@app.route("/search_disease", methods=["GET"])
def search_disease():
    query = request.args.get("q", "").strip().lower()
    if not query:
        return jsonify({"success": False, "error": "Empty query"}), 400

    cached = cache_get(query)
    if cached:
        return jsonify({
            "success": True,
            "plants": cached["plants"],
            "source": cached["source"],
            "cached": True
        })

    try:
        db_results = firestore.search_plants_by_disease(query)
        web_results = scrape_plants_for_disease(query)

        final_results = db_results or web_results or []
        source = "firebase" if db_results else "internet"

        cache_set(query, source, final_results)

        return jsonify({
            "success": True,
            "plants": final_results,
            "source": source,
            "cached": False
        })

    except Exception as e:
        print("[ERROR] search_disease:", e)
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------- PREDICT ----------------
@app.route("/predict", methods=["POST"])
def predict():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file"}), 400

    f = request.files["file"]
    filename = secure_filename(f.filename)
    temp_path = os.path.join(UPLOAD_DIR, f"predict_{int(time.time())}_{filename}")
    f.save(temp_path)

    try:
        class_id, confidence = predict_image(temp_path)

        # 🔹 FETCH FROM FIREBASE
        plant = firestore.get_plant_by_no(class_id)

        # 🔹 If plant not found → return Unknown
        if not plant:
            plant = {
                "name": "Unknown",
                "scientific": "N/A",
                "parts": [],
                "uses": "unknown.",
                "region": "Unknown"
            }

        return jsonify({
            "success": True,
            "class_id": class_id,
            "confidence": confidence,
            "plant": plant
        })

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# ---------------- SERVE UPLOADS ----------------
@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(UPLOAD_DIR, filename)


# ---------------- MAIN ----------------
if __name__ == "__main__":
    print("[SERVER] http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)