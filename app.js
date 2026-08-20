// --- 1. CAPAS BASE DEL MAPA ---
const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  maxZoom: 19
});

const esriSat = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
  attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
});

const cartoPositron = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
  attribution: '&copy; <a href="https://carto.com/">CARTO</a>',
  maxZoom: 20
});

const cartoDark = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
  attribution: '&copy; <a href="https://carto.com/">CARTO</a>',
  maxZoom: 20
});

const opentopo = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
  attribution: 'Map data: &copy; OpenStreetMap contributors, SRTM | Map style: &copy; OpenTopoMap',
  maxZoom: 17
});

// Inicialización del Mapa
const map = L.map('map', {
  center: [-34.6, -64.0],
  zoom: 5,
  layers: [osm]
});

// Selector de capas (esquina superior derecha)
const baseMaps = {
  "OpenStreetMap": osm,
  "Satelital (Esri)": esriSat,
  "Claro (CartoDB)": cartoPositron,
  "Oscuro (CartoDB)": cartoDark,
  "Topográfico": opentopo
};

L.control.layers(baseMaps).addTo(map);

// Icono personalizado
const fosilIcon = L.divIcon({
  className: '',
  html: '<div class="fosil-icon">🦴</div>',
  iconSize: [26, 26],
  iconAnchor: [13, 13],
  popupAnchor: [0, -13]
});

const cluster = L.markerClusterGroup();
let todosLosMarcadores = [];

// --- 2. NORMALIZACIÓN DE ORGANISMOS ---
function normalizarOrganismo(texto) {
  if (!texto) return "Otros";
  const t = texto.toLowerCase();
  
  if (t.includes("ammonit") || t.includes("ammono") || t.includes("ammonoid")) return "Ammonites";
  if (t.includes("gastropod") || t.includes("caracol") || t.includes("gastro")) return "Gastrópodos";
  if (t.includes("bivalv") || t.includes("ostra") || t.includes("rudista")) return "Bivalvos / Ostras";
  if (t.includes("coral")) return "Corales";
  if (t.includes("nummulit") || t.includes("foramin")) return "Nummulites / Foraminíferos";
  if (t.includes("belemn") || t.includes("belemno")) return "Belemnites";
  if (t.includes("erizo") || t.includes("echino")) return "Erizos de mar";
  if (t.includes("estrella")) return "Estrellas de mar";
  if (t.includes("trazas") || t.includes("cruziana")) return "Trazas fósiles";
  
  return "Otros";
}

// --- 3. CARGA DE REGISTROS Y MARCADORES ---
function cargarPuntos() {
  cluster.clearLayers();
  todosLosMarcadores = [];

  if (typeof fosiles === 'undefined' || !Array.isArray(fosiles)) return;

  fosiles.forEach(f => {
    const marker = L.marker([f.lat, f.lng], { icon: fosilIcon });

    const fotosHtml = f.fotos && f.fotos.length
      ? `<div class="popup-fotos">
          ${f.fotos.map(url => `<img src="${url}" alt="Foto de fósil" loading="lazy" onclick="window.open('${url}', '_blank')">`).join('')}
         </div>`
      : '';

    const popupHtml = `
      <div class="popup-content">
        <h3>${f.titulo || 'Sin título'}</h3>
        ${f.organismo ? `<span class="organismo">${f.organismo}</span>` : ''}
        <p class="direccion">${f.direccion || ''}</p>
        ${fotosHtml}
        <p class="autor">${f.autor || ''}</p>
      </div>
    `;

    marker.bindPopup(popupHtml, { maxWidth: 280 });

    marker.datosFosil = {
      organismoGrupo: normalizarOrganismo(f.organismo),
      autor: f.autor ? f.autor.trim() : "Anónimo"
    };

    todosLosMarcadores.push(marker);
    cluster.addLayer(marker);
  });

  map.addLayer(cluster);

  if (fosiles.length > 0) {
    const bounds = L.latLngBounds(fosiles.map(f => [f.lat, f.lng]));
    map.fitBounds(bounds, { padding: [30, 30] });
  }

  poblarSelects();
}

// --- 4. OPCIONES DE FILTROS ---
function poblarSelects() {
  const selectOrg = document.getElementById("filtro-organismo");
  const selectAut = document.getElementById("filtro-autor");

  selectOrg.innerHTML = '<option value="todos">Todos los organismos</option>';
  selectAut.innerHTML = '<option value="todos">Todos los autores</option>';

  const organismosUnicos = [...new Set(todosLosMarcadores.map(m => m.datosFosil.organismoGrupo))].sort();
  const autoresUnicos = [...new Set(todosLosMarcadores.map(m => m.datosFosil.autor))].sort();

  organismosUnicos.forEach(org => {
    selectOrg.innerHTML += `<option value="${org}">${org}</option>`;
  });

  autoresUnicos.forEach(aut => {
    if (aut && aut !== "Anónimo") {
      selectAut.innerHTML += `<option value="${aut}">${aut}</option>`;
    }
  });
}

// --- 5. APLICACIÓN DE FILTROS ---
function aplicarFiltros() {
  const orgSel = document.getElementById("filtro-organismo").value;
  const autSel = document.getElementById("filtro-autor").value;

  cluster.clearLayers();

  todosLosMarcadores.forEach(m => {
    const cumpleOrg = (orgSel === "todos" || m.datosFosil.organismoGrupo === orgSel);
    const cumpleAut = (autSel === "todos" || m.datosFosil.autor === autSel);

    if (cumpleOrg && cumpleAut) {
      cluster.addLayer(m);
    }
  });
}

// Escuchadores de eventos
document.getElementById("filtro-organismo").addEventListener("change", aplicarFiltros);
document.getElementById("filtro-autor").addEventListener("change", aplicarFiltros);
document.getElementById("toggle-panel").addEventListener("click", () => {
  document.getElementById("contenido-filtros").classList.toggle("oculto");
});

// Inicializar
cargarPuntos();
