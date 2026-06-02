import os
import requests
from utils import firestore

# Folder where auto-grown dataset images will be stored
DATASET_DIR = os.path.join("backend", "dataset")  # safer + consistent path

os.makedirs(DATASET_DIR, exist_ok=True)


def ensure_folder(plant_name: str):
    """
    Ensures dataset/<plant_name>/ exists.
    """
    folder = os.path.join(DATASET_DIR, plant_name)
    os.makedirs(folder, exist_ok=True)
    return folder


def add_image_to_folder(image_url: str, plant_name: str):
    """
    Download the image from Firebase URL → save into dataset folder.
    """
    folder = ensure_folder(plant_name)
    filename = f"{plant_name}_{len(os.listdir(folder)) + 1}.jpg"
    filepath = os.path.join(folder, filename)

    try:
        r = requests.get(image_url, timeout=5)
        if r.status_code == 200:
            with open(filepath, "wb") as f:
                f.write(r.content)
            print("[DATASET] Saved:", filepath)
        else:
            print("[DATASET ERROR] Couldn't download image:", image_url)
    except Exception as e:
        print("[DATASET ERROR]", e)


def create_new_plant_entry(plant_name: str):
    """
    Creates a new plant entry in Firebase after 50 unique user submissions.
    Uses minimal fields to avoid breaking schema.
    """

    next_no = firestore.get_next_plant_no()

    plant_data = {
        "no": next_no,
        "name": plant_name,
        "parts": "Unknown",
        "region": "Unknown",
        "uses": "User-submitted plant. Awaiting admin verification.",
        "diseases": [],
        "image_url": "",  # optional
    }

    firestore.add_plant(plant_data)
    print(f"[DATASET] Firebase entry created for {plant_name} (no={next_no})")

    return next_no


def process_new_submission(plant_name: str, image_url: str, submission_count: int):
    """
    Auto-grow dataset rules:

    ✔ If dataset folder exists → append the new image.
    ✔ If not and submissions < 50 → wait for more user images.
    ✔ Once submissions hit 50 → create folder + download all past images.
    ✔ Then create a new Firebase plant entry.
    """
    plant_folder = os.path.join(DATASET_DIR, plant_name)

    # RULE 1 — Already a dataset class
    if os.path.exists(plant_folder):
        add_image_to_folder(image_url, plant_name)
        return "added_to_existing_dataset"

    # RULE 2 — Wait until 50 submissions
    if submission_count < 50:
        return f"waiting_for_50_submissions_current={submission_count}"

    # RULE 3 — Create dataset folder + add all previous images
    ensure_folder(plant_name)

    print("[DATASET] Creating new dataset folder for:", plant_name)

    # Fetch all previous user submissions
    all_subs = firestore.get_all_submissions(plant_name)
    for sub in all_subs:
        prev_url = sub.get("image_url")
        if prev_url:
            add_image_to_folder(prev_url, plant_name)

    # Add current submission image
    add_image_to_folder(image_url, plant_name)

    # Add new Firebase plant entry
    new_no = create_new_plant_entry(plant_name)

    return f"new_dataset_created_and_firebase_entry_added_no_{new_no}"
