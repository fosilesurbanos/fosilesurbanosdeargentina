```python
import os
import json
import requests

from PIL import Image
from io import BytesIO
from datetime import datetime
from urllib.parse import urlparse, parse_qs, unquote


PROJECT_SLUG = "fosiles-urbanos-de-argentina"

BASE_URL = (
    f"https://five.epicollect.net/api/export/entries/"
    f"{PROJECT_SLUG}?format=json&per_page=100"
)

IMAGES_DIR = "fotos"
BACKUP_DIR = "backups"

os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)


# ---------------------------------------------------------
# PROCESAMIENTO DE IMÁGENES
# ---------------------------------------------------------

def get_photo_filename(url):
    """
    Obtiene un nombre de archivo limpio a partir de la URL
    de una fotografía de Epicollect5.

    Ejemplo de URL actual:

    https://five.epicollect.net/api/media/...
        ?type=photo
        &format=entry_original
        &name=82f86cf0-....jpg
        &v=1787572531

    Devuelve solamente:

    82f86cf0-....jpg
    """

    try:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        # Epicollect normalmente proporciona el nombre mediante ?name=
        if "name" in query and query["name"]:
            filename = unquote(query["name"][0])
        else:
            filename = os.path.basename(parsed.path)

        # Eliminar posibles parámetros o espacios residuales
        filename = filename.split("?")[0].split("&")[0].strip()

        # Si no tiene extensión reconocible, usar JPG
        lower = filename.lower()

        if lower.endswith(".jpeg"):
            filename = filename[:-5] + ".jpg"
        elif lower.endswith(".png"):
            filename = filename[:-4] + ".jpg"
        elif lower.endswith(".jpg"):
            pass
        else:
            filename += ".jpg"

        return filename

    except Exception as e:
        print(f"Error obteniendo nombre de archivo desde {url}: {e}")

        # Último recurso
        return f"foto_{abs(hash(url))}.jpg"


def process_image(url, filename):
    """
    Descarga una imagen de Epicollect5, la reduce a un máximo
    de 800x800 px y la guarda como JPG.

    Si la imagen ya existe localmente, no vuelve a descargarla.
    """

    filepath = os.path.join(IMAGES_DIR, filename)

    # No descargar nuevamente imágenes que ya tenemos
    if os.path.exists(filepath):
        return f"{IMAGES_DIR}/{filename}"

    try:
        print(f"Descargando imagen: {filename}")

        response = requests.get(url, timeout=30)

        if response.status_code != 200:
            print(
                f"Error descargando imagen "
                f"{url}: HTTP {response.status_code}"
            )
            return None

        img = Image.open(BytesIO(response.content))

        # Convertir a RGB para poder guardar como JPEG
        if img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, "white")

            if img.mode == "P":
                img = img.convert("RGBA")

            background.paste(
                img,
                mask=img.getchannel("A") if "A" in img.getbands() else None
            )

            img = background

        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Máximo 800 px de ancho/alto conservando proporción
        img.thumbnail((800, 800))

        # Asegurarnos de que el nombre termina en .jpg
        if not filename.lower().endswith(".jpg"):
            filename = os.path.splitext(filename)[0] + ".jpg"
            filepath = os.path.join(IMAGES_DIR, filename)

        img.save(
            filepath,
            "JPEG",
            quality=75,
            optimize=True
        )

        print(f"  ✓ Guardada: {filepath}")

        return f"{IMAGES_DIR}/{filename}"

    except Exception as e:
        print(f"Error procesando imagen {url}: {e}")
        return None


# ---------------------------------------------------------
# DETECCIÓN DE FOTOGRAFÍAS
# ---------------------------------------------------------

def is_epicollect_photo(value):
    """
    Determina si un valor es una URL de fotografía de Epicollect5.

    No comprueba si la URL termina en .jpg porque Epicollect5
    actualmente agrega parámetros como:

        &v=1787572531

    después del nombre del archivo.
    """

    if not isinstance(value, str):
        return False

    value_lower = value.lower()

    # Tiene que ser una URL de Epicollect5
    if "five.epicollect.net" not in value_lower:
        return False

    # Debe ser una URL de media/foto
    if "/api/media/" not in value_lower:
        return False

    # Intentar comprobar que tiene un nombre de archivo
    try:
        parsed = urlparse(value)
        query = parse_qs(parsed.query)

        if "name" in query and query["name"]:
            filename = unquote(query["name"][0]).lower()

            return filename.endswith(
                (".jpg", ".jpeg", ".png")
            )

    except Exception:
        pass

    return False


def extract_photos(entry):
    """
    Busca todas las fotografías de un registro de Epicollect5.

    No depende del nombre del campo de la fotografía.
    """

    photos = []

    for key, value in entry.items():

        if is_epicollect_photo(value):
            photos.append(value)

    return photos


# ---------------------------------------------------------
# EXTRACCIÓN DE DATOS
# ---------------------------------------------------------

def extract_val(entry, keywords):
    """
    Busca un valor textual en las claves del registro.
    """

    for key, val in entry.items():

        if val is None:
            continue

        key_lower = key.lower()

        for kw in keywords:

            if kw in key_lower:

                # Evitar convertir diccionarios/listas
                # accidentalmente en texto
                if isinstance(val, (dict, list)):
                    continue

                return str(val).strip()

    return ""


# ---------------------------------------------------------
# LECTURA DEL DATA.JS EXISTENTE
# ---------------------------------------------------------

def count_existing_records():
    """
    Cuenta cuántos registros hay actualmente guardados
    en data.js.
    """

    if not os.path.exists("data.js"):
        return 0

    try:

        with open("data.js", "r", encoding="utf-8") as f:
            content = f.read()

        json_str = (
            content
            .replace("const fosiles = ", "")
            .rstrip(";\n")
        )

        existing_data = json.loads(json_str)

        return len(existing_data)

    except Exception as e:

        print(f"Error al leer data.js previo: {e}")

        return 0


# ---------------------------------------------------------
# SINCRONIZACIÓN
# ---------------------------------------------------------

def sync():

    url = BASE_URL
    entries = []

    # -----------------------------------------------------
    # OBTENER TODOS LOS REGISTROS DE EPICOLLECT
    # -----------------------------------------------------

    while url:

        try:

            print(f"Consultando Epicollect5...")

            res = requests.get(url, timeout=30)

            if res.status_code != 200:

                print(
                    f"Error al conectar con la API: "
                    f"{res.status_code}"
                )

                break

            json_data = res.json()

            data_block = json_data.get("data", {})

            page_entries = data_block.get("entries", [])

            # Compatibilidad por si Epicollect devuelve
            # directamente una lista
            if not page_entries and isinstance(data_block, list):
                page_entries = data_block

            entries.extend(page_entries)

            url = json_data.get("links", {}).get("next")

        except Exception as e:

            print(
                f"Error en la petición a Epicollect: {e}"
            )

            break

    # -----------------------------------------------------
    # PROTECCIÓN CONTRA RESPUESTAS ANORMALES
    # -----------------------------------------------------

    total_nuevos = len(entries)
    total_previos = count_existing_records()

    print(
        f"Registros previos en web: {total_previos} | "
        f"Registros obtenidos hoy: {total_nuevos}"
    )

    # Si teníamos datos y la API devuelve 0 o menos
    # de la mitad, cancelamos la actualización.
    if total_previos > 0 and total_nuevos < (total_previos / 2):

        print(
            "⚠️ ALERTA: La cantidad de registros devueltos "
            "por Epicollect es sospechosamente baja o cero."
        )

        print(
            "Cancelando la actualización de data.js "
            "para proteger la base de datos existente."
        )

        return

    # -----------------------------------------------------
    # PROCESAR REGISTROS
    # -----------------------------------------------------

    fosiles = []

    total_con_fotos = 0
    total_fotos = 0

    for entry in entries:

        # -------------------------------------------------
        # FOTOGRAFÍAS
        # -------------------------------------------------

        raw_photos = extract_photos(entry)

        if raw_photos:
            total_con_fotos += 1

        local_photos = []

        for photo_url in raw_photos:

            filename = get_photo_filename(photo_url)

            local_path = process_image(
                photo_url,
                filename
            )

            if local_path:
                local_photos.append(local_path)
                total_fotos += 1

        # -------------------------------------------------
        # COORDENADAS
        # -------------------------------------------------

        lat = None
        lng = None

        for key, value in entry.items():

            if (
                isinstance(value, dict)
                and "latitude" in value
                and "longitude" in value
            ):

                lat = value.get("latitude")
                lng = value.get("longitude")

                break

        # Compatibilidad con otros formatos
        if lat is None or lng is None:

            lat = (
                entry.get("latitude")
                or entry.get("lat")
            )

            lng = (
                entry.get("longitude")
                or entry.get("lng")
            )

        # -------------------------------------------------
        # DATOS DEL REGISTRO
        # -------------------------------------------------

        titulo = extract_val(
            entry,
            [
                "titulo",
                "title",
                "lugar",
                "ubicacion",
                "direccion"
            ]
        )

        direccion = extract_val(
            entry,
            [
                "direccion",
                "calle",
                "address"
            ]
        ) or titulo

        organismo = extract_val(
            entry,
            [
                "organismo",
                "fosil",
                "especie",
                "tipo"
            ]
        )

        autor = extract_val(
            entry,
            [
                "autor",
                "encontrado",
                "usuario",
                "creador",
                "created_by"
            ]
        )

        fecha = (
            entry.get("created_at")
            or entry.get("uploaded_at")
            or ""
        )

        # -------------------------------------------------
        # CREAR REGISTRO
        # -------------------------------------------------

        if lat is not None and lng is not None:

            try:

                fosiles.append(
                    {
                        "id": entry.get(
                            "ec5_uuid",
                            entry.get("id", "")
                        ),

                        "lat": float(lat),

                        "lng": float(lng),

                        "titulo": (
                            titulo
                            or "Sin título"
                        ),

                        "direccion": direccion,

                        "organismo": organismo,

                        "autor": autor,

                        "fecha": str(fecha),

                        "fotos": local_photos
                    }
                )

            except (ValueError, TypeError):

                print(
                    "⚠️ Registro descartado por "
                    "coordenadas inválidas:"
                )

                print(entry.get("ec5_uuid", ""))

                continue

    # -----------------------------------------------------
    # GUARDAR DATA.JS
    # -----------------------------------------------------

    with open(
        "data.js",
        "w",
        encoding="utf-8"
    ) as f:

        f.write("const fosiles = ")

        f.write(
            json.dumps(
                fosiles,
                indent=2,
                ensure_ascii=False
            )
        )

        f.write(";\n")

    # -----------------------------------------------------
    # BACKUP
    # -----------------------------------------------------

    hoy = datetime.now().strftime("%Y-%m-%d")

    backup_filename = os.path.join(
        BACKUP_DIR,
        f"data_backup_{hoy}.json"
    )

    with open(
        backup_filename,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            fosiles,
            f,
            indent=2,
            ensure_ascii=False
        )

    # -----------------------------------------------------
    # INFORME FINAL
    # -----------------------------------------------------

    print()
    print("========================================")
    print("SINCRONIZACIÓN COMPLETADA")
    print("========================================")

    print(
        f"Registros obtenidos: {total_nuevos}"
    )

    print(
        f"Fósiles escritos: {len(fosiles)}"
    )

    print(
        f"Registros con fotografías: "
        f"{total_con_fotos}"
    )

    print(
        f"Fotografías procesadas: "
        f"{total_fotos}"
    )

    print(
        f"Backup creado: "
        f"{backup_filename}"
    )

    print("========================================")


# ---------------------------------------------------------
# EJECUCIÓN
# ---------------------------------------------------------

if __name__ == "__main__":
    sync()
```
