import requests
from bs4 import BeautifulSoup
import re
import spacy

# ---------------------------------------------------------
# LOAD SPACY NLP MODEL
# ---------------------------------------------------------
try:
    nlp = spacy.load("en_core_web_sm")
except Exception:
    import os
    os.system("python -m spacy download en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

# ---------------------------------------------------------
# DISEASE / SYMPTOM SYNONYM MAP
# ---------------------------------------------------------
DISEASE_ALIASES = {
    "cough": "herbs for cough relief",
    "dry cough": "herbs for dry cough",
    "wet cough": "herbs for productive cough",
    "cough with phlegm": "herbs for cough with phlegm",
    "cold": "herbs for common cold",
    "flu": "herbal flu treatment",
    "fever": "herbal treatment for fever",
    "viral fever": "herbal treatment for viral fever",
    "chills": "fever and chills herbal remedies",
    "headache": "herbs for headache relief",
    "migraine": "herbs for migraine treatment",
    "toothache": "herbs for toothache pain",
    "tooth pain": "herbs for toothache",
    "sore throat": "herbs for sore throat",
    "throat pain": "herbs for throat infection",
    "asthma": "herbs for asthma",
    "bronchitis": "herbs for bronchitis",
    "sinusitis": "herbs for sinus infection",
    "allergies": "herbs for allergy relief",
    "acne": "herbs for acne treatment",
    "pimples": "herbs for acne",
    "anemia": "herbs for anemia",
    "stomach pain": "herbs for stomach pain",
    "indigestion": "herbs for indigestion",
    "gas": "herbs for gas and bloating",
    "acid reflux": "herbs for acid reflux",
    "diarrhea": "herbs for diarrhea",
    "diabetes": "diabetes herbal treatment",
    "hypertension": "herbs for hypertension",
    "burn": "herbs for burn healing",
    "wound": "wound healing herbs",
    "eczema": "herbs for eczema",
    "psoriasis": "herbs for psoriasis",
    "fungal infection": "herbs for fungal skin infection",
    "ear pain": "herbs for ear pain",
    "nausea": "herbs for nausea",
    "hair loss": "herbs for hair loss",
    "piles": "herbs for piles",
}

# ---------------------------------------------------------
# CLEAN TEXT
# ---------------------------------------------------------
def clean(text: str) -> str:
    return re.sub(r"\[\d+\]", "", text).replace("\n", " ").strip()

# ---------------------------------------------------------
# NLP PLANT EXTRACTION (STRICT)
# ---------------------------------------------------------
EXCLUDED_TERMS = {
    "Peas", "Oil", "Leaf", "Leaves", "Water", "Milk",
    "Protein", "Vitamin", "Rice", "Wheat"
}

def extract_plants(text: str):
    doc = nlp(text)
    names = []

    for ent in doc.ents:
        if ent.label_ in {"ORG", "PERSON", "DATE"}:
            continue
        if ent.text in EXCLUDED_TERMS:
            continue
        if ent.text and ent.text[0].isupper() and len(ent.text.split()) <= 3:
            names.append(ent.text.strip())

    return list(dict.fromkeys(names))  # preserve order

# ---------------------------------------------------------
# WIKIPEDIA SCRAPER
# ---------------------------------------------------------
def wikipedia_search(query: str):
    url = f"https://en.wikipedia.org/w/index.php?search={query.replace(' ', '+')}"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code != 200:
            return []

        soup = BeautifulSoup(r.text, "html.parser")
        text = clean(" ".join(p.get_text() for p in soup.find_all("p")))

        results = []
        for plant in extract_plants(text):
            for s in text.split("."):
                if plant.lower() in s.lower():
                    results.append({
                        "name": plant,
                        "uses": s.strip()[:220] + "...",
                        "region": "Wikipedia"
                    })
                    break
        return results[:6]
    except Exception:
        return []

# ---------------------------------------------------------
# AYUSH SCRAPER
# ---------------------------------------------------------
def ayush_search(disease: str):
    url = f"https://ayushportal.nic.in/?s={disease.replace(' ', '+')}"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        r = requests.get(url, headers=headers, timeout=6)
        if r.status_code != 200:
            return []

        soup = BeautifulSoup(r.text, "html.parser")
        text = clean(" ".join(a.get_text(" ") for a in soup.find_all("article")))

        results = []
        for plant in extract_plants(text):
            for s in text.split("."):
                if plant.lower() in s.lower():
                    results.append({
                        "name": plant,
                        "uses": s.strip()[:220] + "...",
                        "region": "AYUSH"
                    })
                    break
        return results[:6]
    except Exception:
        return []

# ---------------------------------------------------------
# FALLBACK DATABASE (KEEP AS YOU HAVE IT)
FALLBACK_DATABASE = {

    # ---------------- BATCH 1: RESPIRATORY ----------------
    "cough": [
        {"name": "Tulsi", "uses": "Reduces cough and throat irritation.", "region": "India"},
        {"name": "Ginger", "uses": "Helps loosen mucus.", "region": "Asia"},
        {"name": "Licorice Root", "uses": "Coats and soothes throat.", "region": "Asia"},
    ],
    "cold": [
        {"name": "Peppermint", "uses": "Opens nasal passages.", "region": "Worldwide"},
        {"name": "Ginger", "uses": "Warms body and reduces cold symptoms.", "region": "Asia"},
        {"name": "Echinacea", "uses": "Boosts immunity.", "region": "North America"},
    ],
    "sore throat": [
        {"name": "Licorice Root", "uses": "Coats throat.", "region": "Asia"},
        {"name": "Slippery Elm", "uses": "Soothes throat.", "region": "North America"},
        {"name": "Tulsi", "uses": "Reduces throat inflammation.", "region": "India"},
    ],
    "asthma": [
        {"name": "Licorice Root", "uses": "Used to ease airway inflammation.", "region": "Asia"},
        {"name": "Ginger", "uses": "Helps relax bronchial muscles.", "region": "Asia"},
        {"name": "Vasaka (Adhatoda)", "uses": "Ayurvedic herb for asthma and bronchitis.", "region": "India"},
    ],
    "bronchitis": [
        {"name": "Vasaka (Adhatoda)", "uses": "Clears bronchial congestion.", "region": "India"},
        {"name": "Mullein", "uses": "Soothes irritated lungs.", "region": "Europe"},
        {"name": "Thyme", "uses": "Natural expectorant, expels mucus.", "region": "Mediterranean"},
    ],

    # ---------------- BATCH 2: FEVER / IMMUNE ----------------
    "fever": [
        {"name": "Neem", "uses": "Reduces fever and infections.", "region": "India"},
        {"name": "Willow Bark", "uses": "Natural fever reducer.", "region": "Europe"},
        {"name": "Guduchi", "uses": "Ayurvedic immune-support herb.", "region": "India"},
    ],
    "allergies": [
        {"name": "Nettle Leaf", "uses": "Relieves allergy symptoms.", "region": "Europe"},
        {"name": "Butterbur", "uses": "Used for hay fever relief.", "region": "Europe"},
        {"name": "Turmeric", "uses": "Reduces inflammation in allergic conditions.", "region": "India"},
    ],

    # ---------------- BATCH 3: ORAL ----------------
    "toothache": [
        {"name": "Clove", "uses": "Strong natural pain reliever for teeth.", "region": "India"},
        {"name": "Peppermint", "uses": "Reduces tooth pain and freshens breath.", "region": "Worldwide"},
        {"name": "Guava Leaf", "uses": "Traditional mouth rinse for tooth pain.", "region": "Tropics"},
    ],
    "mouth ulcers": [
        {"name": "Licorice Root", "uses": "Soothes mouth ulcers.", "region": "Asia"},
        {"name": "Aloe Vera", "uses": "Promotes healing of ulcers.", "region": "Tropics"},
        {"name": "Turmeric", "uses": "Reduces inflammation in ulcers.", "region": "India"},
    ],

    # ---------------- BATCH 4: SKIN ----------------
    "wound": [
        {"name": "Aloe Vera", "uses": "Heals wounds quickly and cools skin.", "region": "Tropics"},
        {"name": "Turmeric", "uses": "Antiseptic for cuts and injuries.", "region": "India"},
        {"name": "Gotu Kola", "uses": "Improves wound healing and collagen.", "region": "Asia"},
    ],
    "burn": [
        {"name": "Aloe Vera", "uses": "Soothes burns and reduces scars.", "region": "Tropics"},
        {"name": "Lavender Oil", "uses": "Traditionally applied to minor burns.", "region": "Europe"},
        {"name": "Calendula", "uses": "Helps skin repair after minor burns.", "region": "Mediterranean"},
    ],
    "acne": [
        {"name": "Neem", "uses": "Kills acne-causing bacteria.", "region": "India"},
        {"name": "Tea Tree Oil", "uses": "Strong antibacterial spot treatment.", "region": "Australia"},
        {"name": "Aloe Vera", "uses": "Reduces redness and swelling.", "region": "Tropics"},
    ],
    "fungal infection (skin)": [
        {"name": "Tea Tree Oil", "uses": "Kills fungal organisms on skin.", "region": "Australia"},
        {"name": "Neem", "uses": "Used for ringworm and fungal patches.", "region": "India"},
        {"name": "Garlic", "uses": "Traditional topical antifungal.", "region": "Worldwide"},
    ],

    # ---------------- BATCH 5: DIGESTIVE ----------------
    "stomach pain": [
        {"name": "Ginger", "uses": "Reduces cramps and nausea.", "region": "Asia"},
        {"name": "Mint", "uses": "Relieves gas and mild pain.", "region": "Worldwide"},
        {"name": "Chamomile", "uses": "Soothes stomach spasms.", "region": "Europe"},
    ],
    "indigestion": [
        {"name": "Fennel", "uses": "Relieves indigestion and heaviness.", "region": "Mediterranean"},
        {"name": "Peppermint", "uses": "Eases bloating and discomfort.", "region": "Worldwide"},
        {"name": "Ginger", "uses": "Improves digestive fire.", "region": "Asia"},
    ],
    "gas": [
        {"name": "Fennel", "uses": "Reduces gas and bloating.", "region": "Mediterranean"},
        {"name": "Ajwain", "uses": "Excellent for gas and cramps.", "region": "India"},
        {"name": "Ginger", "uses": "Relieves gas buildup.", "region": "Asia"},
    ],
    "diarrhea": [
        {"name": "Bael", "uses": "Classical Ayurvedic remedy for diarrhea.", "region": "India"},
        {"name": "Black Tea", "uses": "Tannins help firm stools.", "region": "Worldwide"},
        {"name": "Chamomile", "uses": "Reduces intestinal inflammation.", "region": "Europe"},
    ],
    "acid reflux": [
        {"name": "Licorice (DGL)", "uses": "Soothes acid irritation.", "region": "Asia"},
        {"name": "Aloe Vera Juice", "uses": "Reduces burning in esophagus.", "region": "Tropics"},
        {"name": "Slippery Elm", "uses": "Protects stomach and throat lining.", "region": "North America"},
    ],

    # ---------------- BATCH 6: PAIN / MUSCLE ----------------
    "back pain": [
        {"name": "Turmeric", "uses": "Reduces back inflammation.", "region": "India"},
        {"name": "Ginger", "uses": "Helps joint stiffness and pain.", "region": "Asia"},
        {"name": "Devil's Claw", "uses": "Traditional herb for chronic pain.", "region": "Africa"},
    ],
    "joint pain": [
        {"name": "Boswellia", "uses": "Ayurvedic joint pain herb.", "region": "India"},
        {"name": "Ginger", "uses": "Anti-inflammatory for joints.", "region": "Asia"},
        {"name": "Turmeric", "uses": "Reduces swelling in joints.", "region": "India"},
    ],
    "muscle pain": [
        {"name": "Peppermint Oil", "uses": "Relieves muscle tension.", "region": "Worldwide"},
        {"name": "Turmeric", "uses": "Reduces muscle inflammation.", "region": "India"},
        {"name": "Ginger", "uses": "Warms and relaxes muscles.", "region": "Asia"},
    ],

    # ---------------- BIG UNIVERSAL FALLBACK: all_plants ----------------
    "all_plants": [
        # SIMPLE GENERIC USES – you can copy lines and modify to reach 300 entries
        {"name": "Tulsi", "uses": "Supports respiratory health and immunity.", "region": "India"},
        {"name": "Neem", "uses": "Supports skin and blood purification.", "region": "India"},
        {"name": "Ashwagandha", "uses": "Supports stress relief and vitality.", "region": "India"},
        {"name": "Turmeric", "uses": "Supports joint comfort and general wellness.", "region": "India"},
        {"name": "Ginger", "uses": "Supports digestion and nausea relief.", "region": "Asia"},
        {"name": "Amla", "uses": "Supports immunity and antioxidant protection.", "region": "India"},
        {"name": "Triphala", "uses": "Supports bowel regularity and detox.", "region": "India"},
        {"name": "Shatavari", "uses": "Supports female reproductive health.", "region": "India"},
        {"name": "Licorice Root", "uses": "Supports throat and digestive comfort.", "region": "Asia"},
        {"name": "Peppermint", "uses": "Supports digestion and fresh breath.", "region": "Worldwide"},
        {"name": "Fennel", "uses": "Supports digestion and gas relief.", "region": "Mediterranean"},
        {"name": "Coriander", "uses": "Supports digestion and cooling.", "region": "Worldwide"},
        {"name": "Cumin", "uses": "Supports digestive function.", "region": "India"},
        {"name": "Cardamom", "uses": "Supports digestion and fresh breath.", "region": "India"},
        {"name": "Cinnamon", "uses": "Supports blood sugar balance.", "region": "Asia"},
        {"name": "Fenugreek", "uses": "Supports blood sugar and lactation.", "region": "Asia"},
        {"name": "Bitter Gourd", "uses": "Supports healthy blood sugar levels.", "region": "India"},
        {"name": "Insulin Plant", "uses": "Supports glucose metabolism.", "region": "India"},
        {"name": "Guduchi", "uses": "Supports immunity and fever management.", "region": "India"},
        {"name": "Vasaka", "uses": "Supports lungs and bronchial health.", "region": "India"},
        {"name": "Mulethi", "uses": "Supports throat comfort and cough relief.", "region": "India"},
        {"name": "Eucalyptus", "uses": "Supports easier breathing.", "region": "Australia"},
        {"name": "Thyme", "uses": "Supports respiratory and immune health.", "region": "Mediterranean"},
        {"name": "Oregano", "uses": "Supports immunity and gut health.", "region": "Mediterranean"},
        {"name": "Basil", "uses": "Supports digestion and immunity.", "region": "Worldwide"},
        {"name": "Marjoram", "uses": "Supports digestion and relaxation.", "region": "Mediterranean"},
        {"name": "Lemongrass", "uses": "Supports digestion and relaxation.", "region": "Asia"},
        {"name": "Chamomile", "uses": "Supports calmness and digestion.", "region": "Europe"},
        {"name": "Valerian", "uses": "Supports sleep and relaxation.", "region": "Europe"},
        {"name": "Passionflower", "uses": "Supports relaxation and calm.", "region": "Americas"},
        {"name": "Brahmi", "uses": "Supports memory and concentration.", "region": "India"},
        {"name": "Gotu Kola", "uses": "Supports circulation and brain health.", "region": "Asia"},
        {"name": "Ginkgo Biloba", "uses": "Supports brain and circulation.", "region": "China"},
        {"name": "Jatamansi", "uses": "Supports stress relief and mind calmness.", "region": "Himalayas"},
        {"name": "Lemon Balm", "uses": "Supports mood and digestion.", "region": "Europe"},
        {"name": "Skullcap", "uses": "Supports nervous system relaxation.", "region": "North America"},
        {"name": "St John’s Wort", "uses": "Supports mood balance.", "region": "Europe"},
        {"name": "Holy Basil (Tulsi)", "uses": "Supports stress response and immunity.", "region": "India"},
        {"name": "Black Pepper", "uses": "Supports digestion and nutrient absorption.", "region": "India"},
        {"name": "Long Pepper", "uses": "Supports respiratory health and digestion.", "region": "India"},
        {"name": "Haritaki", "uses": "Supports detox and bowel health.", "region": "India"},
        {"name": "Bibhitaki", "uses": "Supports respiratory and digestive health.", "region": "India"},
        {"name": "Punarnava", "uses": "Supports kidney and fluid balance.", "region": "India"},
        {"name": "Arjuna", "uses": "Supports heart health and circulation.", "region": "India"},
        {"name": "Guggulu", "uses": "Supports joint and metabolic health.", "region": "India"},
        {"name": "Shankhapushpi", "uses": "Supports memory and calm mind.", "region": "India"},
        {"name": "Hibiscus", "uses": "Supports blood pressure and heart health.", "region": "Tropics"},
        {"name": "Dandelion", "uses": "Supports liver and kidney function.", "region": "Worldwide"},
        {"name": "Milk Thistle", "uses": "Supports liver protection.", "region": "Europe"},
        {"name": "Nettle Leaf", "uses": "Supports joints and seasonal comfort.", "region": "Europe"},
        {"name": "Burdock Root", "uses": "Supports skin and liver health.", "region": "Europe"},
        {"name": "Red Clover", "uses": "Supports skin and hormonal balance.", "region": "Europe"},
        {"name": "Evening Primrose", "uses": "Supports skin and women’s health.", "region": "Europe"},
        {"name": "Saw Palmetto", "uses": "Supports prostate health.", "region": "North America"},
        {"name": "Pygeum", "uses": "Supports urinary and prostate health.", "region": "Africa"},
        {"name": "Horsetail", "uses": "Supports hair, skin and nails.", "region": "Europe"},
        {"name": "Rosemary", "uses": "Supports memory and digestion.", "region": "Mediterranean"},
        {"name": "Sage", "uses": "Supports memory and throat health.", "region": "Mediterranean"},
        {"name": "Lavender", "uses": "Supports relaxation and sleep.", "region": "Europe"},
        {"name": "Calendula", "uses": "Supports skin healing and soothing.", "region": "Mediterranean"},
        {"name": "Aloe Vera", "uses": "Supports skin healing and digestion.", "region": "Tropics"},
        {"name": "Tea Tree", "uses": "Supports skin and scalp health.", "region": "Australia"},
        {"name": "Witch Hazel", "uses": "Supports skin tone and comfort.", "region": "North America"},
        {"name": "Plantain Leaf", "uses": "Supports skin and wound comfort.", "region": "Worldwide"},
        {"name": "Yarrow", "uses": "Supports wound care and circulation.", "region": "Europe"},
        {"name": "Comfrey", "uses": "Supports tissue and bone recovery.", "region": "Europe"},
        {"name": "Devil’s Claw", "uses": "Supports joint and back comfort.", "region": "Africa"},
        {"name": "White Willow Bark", "uses": "Supports pain and fever relief.", "region": "Europe"},
        {"name": "Cranberry", "uses": "Supports urinary tract health.", "region": "North America"},
        {"name": "Bearberry (Uva Ursi)", "uses": "Supports urinary tract function.", "region": "Europe"},
        {"name": "Corn Silk", "uses": "Supports urinary comfort.", "region": "Worldwide"},
        {"name": "Licorice", "uses": "Supports digestion and respiratory health.", "region": "Asia"},
        {"name": "Moringa", "uses": "Supports nutrition and antioxidant status.", "region": "India"},
        {"name": "Giloy", "uses": "Supports immunity and general wellness.", "region": "India"},
        {"name": "Kalonji (Black Seed)", "uses": "Supports immunity and metabolism.", "region": "Asia"},
        {"name": "Bael", "uses": "Supports bowel health and diarrhea management.", "region": "India"},
        {"name": "Shilajit", "uses": "Supports energy and stamina.", "region": "Himalayas"},
        {"name": "Tulsi Krishna", "uses": "Supports respiration and stress response.", "region": "India"},
        {"name": "Senna", "uses": "Supports bowel movement relief.", "region": "India"},
        {"name": "Isabgol (Psyllium)", "uses": "Supports fiber intake and bowel function.", "region": "India"},
        {"name": "Garlic", "uses": "Supports heart and immune health.", "region": "Worldwide"},
        {"name": "Onion", "uses": "Supports circulation and immunity.", "region": "Worldwide"},
        {"name": "Mint", "uses": "Supports fresh breath and digestion.", "region": "Worldwide"},
        {"name": "Curry Leaves", "uses": "Supports digestion and metabolism.", "region": "India"},
        {"name": "Guava Leaf", "uses": "Supports oral and digestive health.", "region": "Tropics"},
        {"name": "Papaya Leaf", "uses": "Supports platelet count and digestion.", "region": "Tropics"},
        {"name": "Coconut", "uses": "Supports hydration and nutrition.", "region": "Tropics"},
        {"name": "Tulsi Rama", "uses": "Supports respiratory and immune health.", "region": "India"},
        # 👉 To reach 300: copy any line below, change the `name` and simple `uses` text.
        # e.g. {"name": "Herb X", "uses": "Supports general wellness.", "region": "India"},
    ],
}

# ---------------------------------------------------------
# BACKWARD COMPATIBILITY
# ---------------------------------------------------------
def scrape_wikipedia_for_disease(disease: str):
    query = DISEASE_ALIASES.get(disease.lower().strip(), f"herbs for {disease}")
    return wikipedia_search(query)

# ---------------------------------------------------------
# MASTER FUNCTION (FIXED PRIORITY)
# ---------------------------------------------------------
def scrape_plants_for_disease(disease: str):
    key = (disease or "").lower().strip()
    print("[SCRAPER] Searching:", key)

    results = []

    # ✅ 1. CURATED FALLBACK FIRST (MOST IMPORTANT)
    if key in FALLBACK_DATABASE:
        results.extend(FALLBACK_DATABASE[key])

    # ✅ 2. AYUSH
    results.extend(ayush_search(key))

    # ✅ 3. WIKIPEDIA
    search_term = DISEASE_ALIASES.get(key, f"herbs for {key}")
    results.extend(wikipedia_search(search_term))

    # Deduplicate
    seen = set()
    final = []
    for r in results:
        name = r["name"].lower()
        if name not in seen:
            seen.add(name)
            final.append(r)

    # ✅ 4. GLOBAL FALLBACK
    if not final:
        final = FALLBACK_DATABASE.get("all_plants", [])[:8]

    return final[:12]
