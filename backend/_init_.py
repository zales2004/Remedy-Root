# backend/utils/__init__.py
from .predict import predict_image
from . import firestore  # exposes firestore.init_firebase, get_all_plants, etc.
