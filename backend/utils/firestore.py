# backend/utils/firestore.py
import json
import firebase_admin
from firebase_admin import credentials, firestore as _fs

_db = None


# ---------------------------------------------------------
# INITIALIZE FIREBASE
# ---------------------------------------------------------
def init_firebase(config_path: str):
    """
    Initialize Firebase using the service account JSON at config_path.
    Called from app.py at startup.
    """
    global _db
    if _db is not None:
        return _db

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    cred = credentials.Certificate(config)

    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred, {
            "projectId": config.get("project_id")
        })

    _db = _fs.client()
    return _db


def get_db():
    """Return Firestore client instance."""
    global _db
    if _db is None:
        raise RuntimeError("Firebase not initialized. Call init_firebase() first.")
    return _db


# ---------------------------------------------------------
# PLANTS COLLECTION CRUD
# ---------------------------------------------------------
def get_all_plants():
    """
    Returns all plant documents from Firestore.
    """
    db = get_db()
    col = db.collection("plants").stream()
    plants = []

    for doc in col:
        data = doc.to_dict()
        data["id"] = doc.id
        plants.append(data)

    return plants


def get_plant_by_no(class_id: int):
    """
    Get a plant by its model class number ("no").
    """
    db = get_db()
    query = db.collection("plants").where("no", "==", class_id).limit(1).stream()

    for doc in query:
        data = doc.to_dict()
        data["id"] = doc.id
        return data

    return None


def add_plant(plant_data: dict):
    """
    Add a new plant entry to Firestore.
    """
    db = get_db()
    doc_ref = db.collection("plants").document()
    doc_ref.set(plant_data)
    plant_data["id"] = doc_ref.id
    return plant_data


def search_plants_by_disease(disease_query: str):
    """
    Search for plants whose 'uses' or 'diseases' match the query.
    """
    disease_query = disease_query.lower()
    plants = get_all_plants()
    results = []

    for p in plants:
        # Search inside "uses"
        uses_text = (p.get("uses") or "").lower()
        if disease_query in uses_text:
            results.append(p)
            continue

        # Search inside diseases[]
        diseases = p.get("diseases", [])
        if isinstance(diseases, list):
            for d in diseases:
                if disease_query in d.lower():
                    results.append(p)
                    break

    return results


# ---------------------------------------------------------
# NEW FEATURE 1:
# Get submission count → used to auto-grow dataset after 50 uploads
# ---------------------------------------------------------
def get_submission_count(plant_name: str) -> int:
    db = get_db()
    count_query = (
        db.collection("submissions")
        .where("plant_name", "==", plant_name)
        .count()
        .get()
        .count
    )
    return count_query


# ---------------------------------------------------------
# NEW FEATURE 2:
# Fetch all submission documents (image URLs) for dataset creation
# ---------------------------------------------------------
def get_all_submissions(plant_name: str):
    db = get_db()
    docs = (
        db.collection("submissions")
        .where("plant_name", "==", plant_name)
        .stream()
    )
    return [d.to_dict() for d in docs]


# ---------------------------------------------------------
# NEW FEATURE 3:
# Automatically assign next available class ID (no)
# ---------------------------------------------------------
def get_next_plant_no() -> int:
    """
    Finds the highest current 'no' and returns next number.
    Ensures no conflicts in model class indexing.
    """
    plants = get_all_plants()
    numbers = []

    for p in plants:
        if "no" in p:
            try:
                numbers.append(int(p["no"]))
            except:
                pass

    return (max(numbers) + 1) if numbers else 0
