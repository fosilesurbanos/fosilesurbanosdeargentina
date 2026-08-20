import os
import requests
from PIL import Image
from io import BytesIO

PROJECT_SLUG = "fosiles-urbanos-de-argentina"
API_URL = f"https://five.epicollect.net/api/export/entries/{PROJECT_SLUG}?format=json"
IMAGES_DIR = "fotos"

os.makedirs(IMAGES_DIR, exist_ok=True)

def process_image(url, filename):
    filepath = os.path.join(IMAGES_DIR, filename)
    # Si ya existe localmente, no la descargamos de nuevo
    if os.path.exists(filepath):
        return f"{IMAGES_DIR}/{filename}"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            img.thumbnail((800, 800)) # Reduce el tamaño manteniendo proporción
            
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
                
            img.save(filepath, "JPEG", quality=75, optimize=True)
            return f"{IMAGES_DIR}/{filename}"
    except Exception as e:
        print(f"Error procesando {url}: {e}")
    return url # En caso de error, mantiene la URL original

def sync():
    res = requests.get(API_URL)
    data = res.json()
    entries = data.get("data", {}).get("entries", [])
    
    fosiles = []
    for entry in entries:
        # Extraer fotos del registro (ajusta la clave si cambia en Epicollect)
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
        
        # Mapeo de campos a la estructura de data.js
        lat, lng = entry.get("location", {}).get("latitude"), entry.get("location", {}).get("longitude")
        if lat and lng:
            fosiles.append({
                "id": entry.get("ec5_uuid"),
                "lat": float(lat),
                "lng": float(lng),
                "titulo": entry.get("title", entry.get("direccion", "Sin título")),
                "direccion": entry.get("direccion", ""),
                "organismo": entry.get("organismo", ""),
                "autor": entry.get("autor", ""),
                "fecha": entry.get("created_at"),
                "fotos": local_photos
            })
            
    # Escribir el nuevo data.js
    with open("data.js", "w", encoding="utf-8") as f:
        f.write("const fosiles = ")
        import json
        f.write(json.dumps(fosiles, indent=2, ensure_ascii=False))
        f.write(";\n")

if __name__ == "__main__":
    sync()