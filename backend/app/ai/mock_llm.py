"""Deterministic offline multilingual intake extractor."""
import re

NEEDS = {
    "RESCUE_BOAT": ["boat", "boats", "terrace", "stranded", "படகு", "நீர் சூழ்ந்த", "नाव"],
    "MEDICAL_TRANSPORT": ["ambulance", "oxygen", "bedridden", "hospital", "ஆக்சிஜன்"],
    "MEDICINE": ["medicine", "medicines", "tablet", "மருந்து", "दवा"],
    "WATER": ["water", "தண்ணீர்", "தண்ணி", "पानी", "drinking water"],
    "FOOD": ["food", "hungry", "meal", "உணவு", "खाना"],
    "SHELTER": ["shelter", "homeless", "stay", "தங்க", "आश्रय"],
    "GENERATOR": ["generator", "ஜெனரேட்டர்"],
    "POWER_BACKUP": ["power", "electricity", "current", "மின்சாரம்", "बिजली"],
    "COOLING": ["cooling", "heat", "fan", "குளிர்"],
    "BLANKETS": ["blanket", "blankets", "கம்பளி"],
    "FUEL": ["fuel", "diesel", "petrol"],
}
VULNS = {"elderly": ["elderly", "old", "senior", "வயதான"], "disabled": ["disabled", "wheelchair"], "infant": ["infant", "baby", "பச்சிளம்"], "pregnant": ["pregnant", "கர்ப்பிணி"], "bedridden": ["bedridden", "நடமாட முடியாது"], "oxygen_dependent": ["oxygen", "ஆக்சிஜன்"]}
LANDMARKS = ["Velachery", "Tambaram", "Adyar", "T. Nagar", "Mylapore", "Perungudi", "Kodambakkam", "Saidapet", "Anna Nagar", "Royapettah", "Guindy", "Besant Nagar", "Sholinganallur", "Chromepet", "Porur"]

def extract(text: str, lat=None, lng=None) -> dict:
    t = text.lower()
    need = next((k for k, words in NEEDS.items() if any(w in t for w in words)), "OTHER")
    if any(w in t for w in ["critical","immediately","life","oxygen","terrace","bedridden","stranded","तुरंत","आपातकाल","உடனே"]): urgency = "CRITICAL"
    elif any(w in t for w in ["urgent","rising","soon","जल्दी","அவசரம்"]): urgency = "HIGH"
    elif need == "OTHER": urgency = "LOW"
    else: urgency = "MEDIUM"
    m = re.search(r"\b(\d{1,4})\b", text)
    qty = float(m.group(1)) if m else (6.0 if "people" in t or "family" in t else None)
    loc = next((x for x in LANDMARKS if x.lower() in t), None)
    flags = [k for k, words in VULNS.items() if any(w in t for w in words)]
    language = "ta" if any(ord(ch) > 0x0B80 and ord(ch) < 0x0BFF for ch in text) else ("hi" if any(ord(ch) > 0x0900 and ord(ch) < 0x097F for ch in text) else "en")
    coords = {"Velachery": (12.9815,80.2180), "Tambaram": (12.9249,80.1000), "Adyar": (13.0067,80.2570), "T. Nagar": (13.0418,80.2341), "Mylapore": (13.0339,80.2690), "Perungudi": (12.9600,80.2460), "Kodambakkam": (13.0524,80.2210), "Saidapet": (13.0213,80.2231), "Anna Nagar": (13.0850,80.2101), "Royapettah": (13.0569,80.2676), "Guindy": (13.0067,80.2206), "Besant Nagar": (12.9992,80.2684), "Sholinganallur": (12.9010,80.2279), "Chromepet": (12.9516,80.1462), "Porur": (13.0358,80.1560)}
    point = coords.get(loc)
    return {"need_type":need,"quantity":qty,"unit":"people" if "people" in t or "family" in t else ("units" if qty is not None else None),"urgency":urgency,"address_text":loc,"lat":lat if lat is not None else (point[0] if point else None),"lng":lng if lng is not None else (point[1] if point else None),"location_confidence":.9 if point or lat is not None else .1,"ward_id":f"WARD-{(LANDMARKS.index(loc)%15)+1:02d}" if loc else None,"vulnerability_flags":flags,"language":language,"translated_text":text,"confidence":.82 if need != "OTHER" else .4}
