# backend/utils/predict.py

import os
import urllib.request
import numpy as np
from PIL import Image
import onnxruntime as ort
import cv2

BASE_DIR   = os.path.dirname(__file__)
MODEL_DIR  = os.path.join(BASE_DIR, "..", "model")
MODEL_PATH = os.path.join(MODEL_DIR, "remedy_root.onnx")

# ── MobileNetV2 (auto-downloaded once, ~14 MB) ───────────────────────────────
MOBILENET_PATH = os.path.join(MODEL_DIR, "mobilenetv2.onnx")
MOBILENET_URL  = "https://github.com/onnx/models/raw/main/validated/vision/classification/mobilenet/model/mobilenetv2-12.onnx"

# ════════════════════════════════════════════════════════════════
# IMAGENET CLASS SETS
# ════════════════════════════════════════════════════════════════

# Classes MobileNetV2 considers plant-like
PLANT_CLASSES = {
    # flowers, plants, fungi, moss
    *range(984, 1000),
    # vegetables with visible leaves
    *range(926, 950),
    # trees / ferns / bamboo
    340, 341,
}

# Classes that are clearly NOT a plant
NOT_PLANT_CLASSES = {
    *range(0,   10),   # people
    *range(30,  150),  # animals / insects / fish
    *range(151, 295),  # more animals
    *range(400, 540),  # vehicles
    *range(559, 620),  # furniture
    *range(620, 720),  # electronics
    # junk food (NOT vegetables)
    925, 927, 928, 929, 930, 932, 933, 934, 935,
}

# ════════════════════════════════════════════════════════════════
# TUNABLE THRESHOLDS  — adjust here only
# ════════════════════════════════════════════════════════════════

CONF_THRESHOLD       = 0.55  # main model confidence

# MobileNetV2 gates
MOB_NOT_PLANT_CONF   = 0.60   # reject if top-1 is non-plant AND confidence > this
MOB_PLANT_MIN        = 0.06   # require at least this much total plant-class probability

# Hard visual reject thresholds
WHITE_BG_MAX         = 0.35   # >35% near-white pixels → product photo background
RED_RATIO_MAX        = 0.015  # >1.5% saturated red pixels → decoration / ribbon
BRIGHT_BLOB_MAX      = 10     # >10 isolated bright blobs → Christmas lights / LEDs
EDGE_RATIO_MAX       = 0.38   # >28% edge pixels → tinsel / garland / ultra-fake

# Leaf quality score  (each component 0–1, weighted sum must exceed threshold)
QUALITY_THRESHOLD    = 0.42  # minimum quality score to pass
W_GREEN_FRACTION     = 0.35   # weight: how much of image is green
W_HUE_VARIATION      = 0.20   # weight: natural hue variation (lowered — succulents like aloe are uniform)
W_SHAPE_COHERENCE    = 0.25   # weight: green region is one coherent blob
W_TEXTURE            = 0.20   # weight: organic texture (Laplacian variance in range)

# ════════════════════════════════════════════════════════════════
# MODEL SESSIONS
# ════════════════════════════════════════════════════════════════

_main_session     = None
_main_input_name  = None
_main_output_name = None
_mob_session      = None
_mob_input_name   = None
_mob_output_name  = None


def _init_main_session():
    global _main_session, _main_input_name, _main_output_name
    if _main_session is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"ONNX model not found: {MODEL_PATH}")
        print("[MODEL] Loading main model...")
        _main_session     = ort.InferenceSession(MODEL_PATH, providers=["CPUExecutionProvider"])
        _main_input_name  = _main_session.get_inputs()[0].name
        _main_output_name = _main_session.get_outputs()[0].name
        print("[MODEL] Main model loaded")


def _init_mobilenet():
    global _mob_session, _mob_input_name, _mob_output_name
    if _mob_session is None:
        if not os.path.exists(MOBILENET_PATH):
            print("[FILTER] Downloading MobileNetV2 (one-time, ~14 MB)...")
            os.makedirs(MODEL_DIR, exist_ok=True)
            urllib.request.urlretrieve(MOBILENET_URL, MOBILENET_PATH)
            print("[FILTER] Download complete")
        _mob_session     = ort.InferenceSession(MOBILENET_PATH, providers=["CPUExecutionProvider"])
        _mob_input_name  = _mob_session.get_inputs()[0].name
        _mob_output_name = _mob_session.get_outputs()[0].name
        print("[FILTER] MobileNetV2 loaded")


# ════════════════════════════════════════════════════════════════
# STAGE 1 — MobileNetV2 TWO-WAY GATE
# Rejects if confidently non-plant AND
# requires minimum plant probability mass.
# This handles all common non-plant objects generically.
# ════════════════════════════════════════════════════════════════

def _mobilenet_gate(img_path):
    _init_mobilenet()

    img = Image.open(img_path).convert("RGB").resize((224, 224))
    arr = np.array(img, dtype="float32")
    arr = (arr / 127.5) - 1.0
    arr = np.transpose(arr, (2, 0, 1))
    arr = np.expand_dims(arr, axis=0)

    logits = _mob_session.run([_mob_output_name], {_mob_input_name: arr})[0][0]
    e      = np.exp(logits - np.max(logits))
    probs  = e / e.sum()

    top_idx  = np.argsort(probs)[::-1][:10]
    top_prob = probs[top_idx]

    print("[MOB] Top-5 classes:", top_idx[:5].tolist())
    print("[MOB] Top-5 probs:  ", np.round(top_prob[:5], 3).tolist())

    top1_class = int(top_idx[0])
    top1_conf  = float(top_prob[0])

   
    if top1_class in NOT_PLANT_CLASSES and top1_conf > MOB_NOT_PLANT_CONF:
        print(f"[REJECT][MOB] Confidently non-plant — class {top1_class}, conf {top1_conf:.2f}")
        return False

   
    print("[MOB] Gate passed")
    return True




def _white_background_check(img_rgb):
    
    white_ratio = np.sum(np.all(img_rgb > 230, axis=2)) / (img_rgb.shape[0] * img_rgb.shape[1])

    
    hsv        = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
    mask       = cv2.inRange(hsv, np.array([25, 35, 35]), np.array([90, 255, 255]))
    green_frac = np.sum(mask > 0) / (img_rgb.shape[0] * img_rgb.shape[1])

    print(f"[CHECK] White bg ratio: {white_ratio:.4f}  Green fraction: {green_frac:.4f}")

    # Only reject if white AND barely any green — e.g. a blank page or screenshot
    if white_ratio > WHITE_BG_MAX and green_frac < 0.10:
        print("[REJECT] White background with no significant green content")
        return False
    return True


def _red_decoration_check(img_rgb):
    """Red ornaments, ribbons, decorative tags — not found on real leaves."""
    hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
    m1  = cv2.inRange(hsv, np.array([0,   100, 80]), np.array([10,  255, 255]))
    m2  = cv2.inRange(hsv, np.array([170, 100, 80]), np.array([180, 255, 255]))
    red_ratio = np.sum((m1 + m2) > 0) / (img_rgb.shape[0] * img_rgb.shape[1])

    green_mask = cv2.inRange(hsv, np.array([25, 35, 35]), np.array([90, 255, 255]))
    green_frac = np.sum(green_mask > 0) / (img_rgb.shape[0] * img_rgb.shape[1])

    print(f"[CHECK] Red ratio: {red_ratio:.5f}  Green fraction: {green_frac:.4f}")

    if red_ratio > RED_RATIO_MAX and green_frac < 0.15:
        print("[REJECT] Red decoration / ribbon detected")
        return False
    return True


def _bright_blob_check(img_rgb):
    """Christmas lights / LEDs create isolated bright blobs on DARK backgrounds.
    Skip this check when background is already white/bright — those blobs are
    just surface reflections (e.g. aloe vera's shiny surface), not lights."""
    # Check background brightness first
    white_ratio = np.sum(np.all(img_rgb > 200, axis=2)) / (img_rgb.shape[0] * img_rgb.shape[1])
    if white_ratio > 0.30:
        # Bright/white background — blob check meaningless, skip it
        print(f"[CHECK] Bright blobs: skipped (white bg {white_ratio:.2f})")
        return True

    hsv         = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
    # Bright warm blobs (lights are warm white / yellow) on dark green background
    bright_mask = cv2.inRange(hsv, np.array([10, 0, 230]), np.array([45, 150, 255]))
    kernel      = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    bright_mask = cv2.morphologyEx(bright_mask, cv2.MORPH_OPEN, kernel)
    n, _, stats, _ = cv2.connectedComponentsWithStats(bright_mask)
    blob_count  = sum(1 for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] > 15)
    print(f"[CHECK] Bright blobs: {blob_count}")
    if blob_count > BRIGHT_BLOB_MAX:
        print("[REJECT] Too many bright blobs — likely decorative lights")
        return False
    return True


def _edge_density_check(img_rgb):
    """Tinsel and garland have thousands of tiny synthetic spikes producing
    extreme edge density. Real leaves never approach this."""
    gray       = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    edges      = cv2.Canny(gray, 60, 140)
    edge_ratio = np.sum(edges > 0) / (img_rgb.shape[0] * img_rgb.shape[1])
    print(f"[CHECK] Edge ratio: {edge_ratio:.4f}")
    if edge_ratio > EDGE_RATIO_MAX:
        print("[REJECT] Extreme edge density — likely tinsel / garland / synthetic fibres")
        return False
    return True


# ════════════════════════════════════════════════════════════════
# STAGE 3 — LEAF QUALITY SCORE
# Instead of individual hard thresholds (which can misfire),
# score 4 independent signals and require a combined minimum.
# A real leaf will score well on most; a fake will fail several.
# ════════════════════════════════════════════════════════════════

def _score_green_fraction(hsv):
    """How much of the image is actual green leaf colour."""
    mask       = cv2.inRange(hsv, np.array([25, 35, 35]), np.array([90, 255, 255]))
    frac       = np.sum(mask > 0) / (hsv.shape[0] * hsv.shape[1])
    # Score peaks at ~40% green coverage, drops off either side
    if frac > 0.75:
        score = 0.0
    else:
        score = float(np.clip(1.0 - abs(frac - 0.40) / 0.40, 0, 1))
    print(f"[SCORE] Green fraction: {frac:.3f}  → score {score:.2f}")
    return score, mask


def _score_hue_variation(hsv, mask, white_bg=False):
    """Natural leaves have organic hue variation. Plastic/fake = flat uniform colour."""
    green_hue = hsv[:, :, 0][mask > 0]
    if len(green_hue) < 200:
        return 0.5
    hue_std = float(np.std(green_hue))
    if white_bg:
        score = 0.5  # studio lighting flattens hue — treat as neutral
        print(f"[SCORE] Hue std: {hue_std:.2f}  → score {score:.2f} (white bg — neutral)")
    else:
        score = float(np.clip((hue_std - 3.0) / 14.0, 0, 1))
        print(f"[SCORE] Hue std: {hue_std:.2f}  → score {score:.2f}")
    return score


def _score_shape_coherence(mask):
    """Green region should be one dominant coherent blob, not scattered fragments."""
    n, _, stats, _ = cv2.connectedComponentsWithStats(mask)
    if n <= 1:
        return 0.0
    areas   = stats[1:, cv2.CC_STAT_AREA]
    largest = float(np.max(areas))
    total   = float(np.sum(mask > 0))
    ratio   = largest / total if total > 0 else 0
    score   = float(np.clip((ratio - 0.20) / 0.60, 0, 1))
    print(f"[SCORE] Shape coherence: {ratio:.3f}  → score {score:.2f}")
    return score


def _score_texture(img_rgb):
    """Real leaves have organic mid-range texture (veins, surface).
    Paper/plastic = too flat. Garland = too chaotic."""
    gray    = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    # Good leaf range: 200–3000. Flat paper: <80. Garland chaos: >5000.
    score   = float(np.clip((lap_var - 80) / 2920, 0, 1))
    score   = score if lap_var < 5000 else max(0, 1.0 - (lap_var - 3000) / 5000)
    print(f"[SCORE] Laplacian var: {lap_var:.1f}  → score {score:.2f}")
    return score


def _leaf_quality_score(img_rgb):
    
    hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)

    white_bg = bool(np.sum(np.all(img_rgb > 200, axis=2)) / (img_rgb.shape[0] * img_rgb.shape[1]) > 0.40)
    s_green, mask = _score_green_fraction(hsv)
    s_hue         = _score_hue_variation(hsv, mask, white_bg=white_bg)
    s_shape       = _score_shape_coherence(mask)
    s_texture     = _score_texture(img_rgb)

    total = (W_GREEN_FRACTION * s_green +
             W_HUE_VARIATION  * s_hue   +
             W_SHAPE_COHERENCE * s_shape +
             W_TEXTURE        * s_texture)

    print(f"[SCORE] Final leaf quality score: {total:.3f}  (threshold {QUALITY_THRESHOLD})")
    return total


# ════════════════════════════════════════════════════════════════
# IMAGE PREPROCESS  (for main model — unchanged)
# ════════════════════════════════════════════════════════════════

def _preprocess_image(img_path, target_size=(224, 224)):
    img = Image.open(img_path).convert("RGB").resize(target_size)
    arr = np.array(img, dtype="float32")
    return np.expand_dims(arr, axis=0)


# ════════════════════════════════════════════════════════════════
# MAIN PREDICTION  (same signature as always)
# ════════════════════════════════════════════════════════════════

def predict_image(img_path):
    print("\n==============================")
    print("[PREDICT] New prediction")
    print("Image:", img_path)

    # ── Stage 1: MobileNetV2 two-way gate ───────────────────────
    if not _mobilenet_gate(img_path):
        print("[RESULT] Rejected (MobileNet gate)")
        return 10000, 0.0

    # ── Stages 2 & 3: pixel-level checks ────────────────────────
    img_bgr = cv2.imread(img_path)
    if img_bgr is not None:
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

        # Hard rejects — any single failure = rejected
        hard_checks = [
            _white_background_check,
            _red_decoration_check,
            _bright_blob_check,
            _edge_density_check,
        ]
        for check in hard_checks:
            if not check(img_rgb):
                print("[RESULT] Rejected (hard visual check)")
                return 10000, 0.0

        # Soft quality score — combined signal
        quality = _leaf_quality_score(img_rgb)
        if quality < QUALITY_THRESHOLD:
            print("[RESULT] Rejected (leaf quality score too low)")
            return 10000, 0.0

    # ── Stage 4: Main disease model ──────────────────────────────
    _init_main_session()
    inp   = _preprocess_image(img_path)
    preds = _main_session.run([_main_output_name], {_main_input_name: inp})[0][0]

    confidence      = float(np.max(preds))
    model_class_idx = int(np.argmax(preds))

    print("[MODEL] Predicted class:", model_class_idx)
    print("[MODEL] Confidence:     ", confidence)

    if confidence < CONF_THRESHOLD:
        print("[REJECT] Confidence too low")
        return 10000, confidence

    print("[RESULT] Prediction accepted")
    return model_class_idx, confidence