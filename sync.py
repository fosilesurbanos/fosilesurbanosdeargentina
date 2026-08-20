import os
import requests
from PIL import Image
from io import BytesIO
import json

PROJECT_SLUG = "fosiles-urbanos-de-argentina"
API_URL = f"https://five.epicollect.net/api/export/entries/{PROJECT_SLUG}?format=json"
IMAGES_DIR = "fotos"

os.makedirs(IMAGES_DIR, exist_ok=True)

def process_image(url, filename):
    filepath = os.path.join(IMAGES_DIR, filename)
    if os.path.exists(filepath):
        return f"{IMAGES_DIR}/{filename}"
    
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            img.thumbnail((800, 800))
            
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
                
            img.save(filepath, "JPEG", quality=75, optimize=True)
            return f"{IMAGES_DIR}/{filename}"
    except Exception as e:
        print(f"Error procesando imagen {url}: {e}")
    return url

def sync():
    res = requests.get(API_URL)
    if res.status_code != 200:
        print("Error al conectar con la API de Epicollect")
        return

    data = res.json()
    entries = data.get("data", {}).get("entries", [])
    
    fosiles = []
    for entry in entries:
        # Extraer fotos
        raw_photos = []
        for k, v in entry.items():
            if isinstance(v, str) and v.endswith(".jpg") and "five.epicollect.net" in v:
                raw_photos.append(v)
        
        local_photos = []
        for photo_url in raw_photos:
            fname = photo_url.split("name=")[-1] if "name=" in photo_url else os.path.basename(photo_url)
            if not fname.endswith(".jpg"):
                fname += ".jpg"
            local_path = process_image(photo_url, fname)
            local_photos.append(local_path)
        
        # Mapeo flexible de coordenadas y textos
        lat = entry.get("location", {}).get("latitude") if isinstance(entry.get("location"), dict) else entry.get("lat")
        lng = entry.get("location", {}).get("longitude") if isinstance(entry.get("location"), dict) else entry.get("lng")
        
        # Buscar campos de texto probando diferentes claves posibles
        titulo = entry.get("titulo") or entry.get("title") or entry.get("direccion") or "Sin título"
        direccion = entry.get("direccion") or entry.get("title") or ""
        organismo = entry.get("organismo") or entry.get("organismos") or ""
        autor = entry.get("autor") or entry.get("created_by") or ""
        fecha = entry.get("created_at") or entry.get("fecha") or ""
        
        if lat and lng:
            try:
                fosiles.append({
                    "id": entry.get("ec5_uuid", entry.get("id")),
                    "lat": float(lat),
                    "lng": float(lng),
                    "titulo": str(titulo),
                    "direccion": str(direccion),
                    "organismo": str(organismo),
                    "autor": str(autor),
                    "fecha": str(fecha),
                    "fotos": local_photos
                })
            except (ValueError, TypeError):
                continue
            
    # Sobrescribir data.js
    with open("data.js", "w", encoding="utf-8") as f:
        f.write("const fosiles = ")
        f.write(json.dumps(fosiles, indent=2, ensure_ascii=False))
        f.write(";\n")

if __name__ == "__main__":
    sync()
