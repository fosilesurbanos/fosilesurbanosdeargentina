import os
import requests
from PIL import Image
from io import BytesIO
import json

PROJECT_SLUG = "fosiles-urbanos-de-argentina"
BASE_URL = f"https://five.epicollect.net/api/export/entries/{PROJECT_SLUG}?format=json&per_page=100"
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

def extract_val(entry, keywords):
    """Busca en el registro de Epicollect una clave que contenga alguna de las palabras clave."""
    for key, val in entry.items():
        if val is None:
            continue
        key_lower = key.lower()
        for kw in keywords:
            if kw in key_lower:
                return str(val).strip()
    return ""

def sync():
    url = BASE_URL
    entries = []
    
    # Recorrer la paginación de Epicollect
    while url:
        res = requests.get(url)
        if res.status_code != 200:
            print(f"Error al conectar con la API: {res.status_code}")
            break
            
        json_data = res.json()
        data_block = json_data.get("data", {})
        
        # Obtener lista de registros
        page_entries = data_block.get("entries", [])
        if not page_entries and isinstance(data_block, list):
            page_entries = data_block
            
        entries.extend(page_entries)
        
        # Pasar a la siguiente página si existe
        url = json_data.get("links", {}).get("next")

    print(f"Total de registros obtenidos desde Epicollect: {len(entries)}")
    
    fosiles = []
    for entry in entries:
        # 1. Extraer URLs de Fotos
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
        
        # 2. Extraer Latitud y Longitud
        lat, lng = None, None
        
        # Caso A: Epicollect guarda un objeto de ubicación
        for k, v in entry.items():
            if isinstance(v, dict) and "latitude" in v and "longitude" in v:
                lat = v.get("latitude")
                lng = v.get("longitude")
                break
                
        # Caso B: Campos planos
        if lat is None or lng is None:
            lat = entry.get("latitude") or entry.get("lat")
            lng = entry.get("longitude") or entry.get("lng")

        # 3. Extraer textos relevantes mediante coincidencia flexible
        titulo = extract_val(entry, ["titulo", "title", "lugar", "ubicacion", "direccion"])
        direccion = extract_val(entry, ["direccion", "calle", "address"]) or titulo
        organismo = extract_val(entry, ["organismo", "fosil", "especie", "tipo"])
        autor = extract_val(entry, ["autor", "encontrado", "usuario", "creador", "created_by"])
        fecha = entry.get("created_at") or entry.get("uploaded_at") or ""
        
        if lat and lng:
            try:
                fosiles.append({
                    "id": entry.get("ec5_uuid", entry.get("id", "")),
                    "lat": float(lat),
                    "lng": float(lng),
                    "titulo": titulo or "Sin título",
                    "direccion": direccion,
                    "organismo": organismo,
                    "autor": autor,
                    "fecha": str(fecha),
                    "fotos": local_photos
                })
            except (ValueError, TypeError):
                continue

    # Guardar en data.js
    with open("data.js", "w", encoding="utf-8") as f:
        f.write("const fosiles = ")
        f.write(json.dumps(fosiles, indent=2, ensure_ascii=False))
        f.write(";\n")
        
    print(f"Éxito: Se escribieron {len(fosiles)} fósiles en data.js")

if __name__ == "__main__":
    sync()
