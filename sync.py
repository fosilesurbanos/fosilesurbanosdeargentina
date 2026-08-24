import os
import requests
from PIL import Image
from io import BytesIO
import json
from datetime import datetime

PROJECT_SLUG = "fosiles-urbanos-de-argentina"
BASE_URL = f"https://five.epicollect.net/api/export/entries/{PROJECT_SLUG}?format=json&per_page=100"
IMAGES_DIR = "fotos"
BACKUP_DIR = "backups"

os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

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
    for key, val in entry.items():
        if val is None:
            continue
        key_lower = key.lower()
        for kw in keywords:
            if kw in key_lower:
                return str(val).strip()
    return ""

def count_existing_records():
    """Cuenta cuántos registros hay actualmente guardados en data.js"""
    if not os.path.exists("data.js"):
        return 0
    try:
        with open("data.js", "r", encoding="utf-8") as f:
            content = f.read()
            json_str = content.replace("const fosiles = ", "").rstrip(";\n")
            existing_data = json.loads(json_str)
            return len(existing_data)
    except Exception as e:
        print(f"Error al leer data.js previo: {e}")
        return 0

def sync():
    url = BASE_URL
    entries = []
    
    # Recorrer paginación de Epicollect
    while url:
        try:
            res = requests.get(url, timeout=15)
            if res.status_code != 200:
                print(f"Error al conectar con la API: {res.status_code}")
                break
                
            json_data = res.json()
            data_block = json_data.get("data", {})
            page_entries = data_block.get("entries", [])
            
            if not page_entries and isinstance(data_block, list):
                page_entries = data_block
                
            entries.extend(page_entries)
            url = json_data.get("links", {}).get("next")
        except Exception as e:
            print(f"Error en la petición a Epicollect: {e}")
            break

    total_nuevos = len(entries)
    total_previos = count_existing_records()
    print(f"Registros previos en web: {total_previos} | Registros obtenidos hoy: {total_nuevos}")

    # PROTECCIÓN DE SEGURIDAD:
    # Si teníamos datos y la API devuelve 0 o cae a menos de la mitad, cancelamos la actualización.
    if total_previos > 0 and total_nuevos < (total_previos / 2):
        print("⚠️ ALERTA: La cantidad de registros devueltos por Epicollect es sospechosamente baja o cero.")
        print("Cancelando la actualización de data.js para proteger la base de datos existente.")
        return

    fosiles = []
    for entry in entries:
        raw_photos = []
        for k, v in entry.items():
    if (
        isinstance(v, str)
        and "five.epicollect.net" in v
        and "name=" in v
    ):
        raw_photos.append(v)
        
        local_photos = []
        for photo_url in raw_photos:
    fname = photo_url.split("name=")[-1].split("&")[0]
    if not fname.lower().endswith((".jpg", ".jpeg", ".png")):
        fname += ".jpg"
    local_path = process_image(photo_url, fname)
    local_photos.append(local_path)
        
        lat, lng = None, None
        for k, v in entry.items():
            if isinstance(v, dict) and "latitude" in v and "longitude" in v:
                lat = v.get("latitude")
                lng = v.get("longitude")
                break
                
        if lat is None or lng is None:
            lat = entry.get("latitude") or entry.get("lat")
            lng = entry.get("longitude") or entry.get("lng")

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

    # Guardar en data.js principal
    with open("data.js", "w", encoding="utf-8") as f:
        f.write("const fosiles = ")
        f.write(json.dumps(fosiles, indent=2, ensure_ascii=False))
        f.write(";\n")

    # CREAR BACKUP CON FECHA DENTRO DE /backups
    hoy = datetime.now().strftime("%Y-%m-%d")
    backup_filename = os.path.join(BACKUP_DIR, f"data_backup_{hoy}.json")
    with open(backup_filename, "w", encoding="utf-8") as f:
        json.dump(fosiles, f, indent=2, ensure_ascii=False)
        
    print(f"Éxito: Se escribieron {len(fosiles)} fósiles en data.js y se creó un backup en {backup_filename}")

if __name__ == "__main__":
    sync()
