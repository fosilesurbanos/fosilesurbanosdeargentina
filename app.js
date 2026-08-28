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
  zoomControl: false,
  layers: [osm]
});

// Selector de capas
const baseMaps = {
  "OpenStreetMap": osm,
  "Satelital (Esri)": esriSat,
  "Claro (CartoDB)": cartoPositron,
  "Oscuro (CartoDB)": cartoDark,
  "Topográfico": opentopo
};

L.control.layers(baseMaps).addTo(map);

// Agregar los botones de Zoom en la esquina superior derecha (quedará ordenado justo debajo de las capas)
L.control.zoom({ position: 'topright' }).addTo(map);

// --- CONTROLES FLOTANTES (APA e Instagram) ABAJO A LA IZQUIERDA ---
const logoControl = L.control({ position: 'bottomleft' });

logoControl.onAdd = function(map) {
  const div = L.DomUtil.create('div', 'map-logo-container');
  div.innerHTML = `
    <!-- Logo de la APA con enlace -->
    <a href="https://www.apaleontologica.org.ar/mapa-de-fosiles-urbanos/" target="_blank" rel="noopener" title="Visitar Asociación Paleontológica Argentina">
      <img src="logoapa.png" alt="Logo APA" class="logo-apa-img" style="height: 80px; width: auto; display: block;">
    </a>
    
    <!-- Ícono de Instagram con enlace -->
    <a href="https://www.instagram.com/fosilesurbanosargentina/" target="_blank" rel="noopener" class="ig-link" title="Seguir en Instagram @fosilesurbanosargentina">
      <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="ig-icon">
        <rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect>
        <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"></path>
        <line x1="17.5" y1="6.5" x2="17.51" y2="6.5"></line>
      </svg>
    </a>
  `;
  return div;
};

logoControl.addTo(map);

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

// --- 2. NORMALIZACIÓN DE ORGANISMOS (Permite Múltiples Categorías) ---
function normalizarOrganismos(texto) {
  if (!texto) return ["Otros"];
  
  // Normalizar removiendo tildes y pasando a minúsculas
  const t = texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  const grupos = [];

  // Ammonites
  if (t.includes("ammonit") || t.includes("ammono") || t.includes("ammonoid")) {
    grupos.push("Ammonitida");
  }

  // Orthocerida (NUEVO)
  if (t.includes("orthocer") || t.includes("ortocer") || t.includes("ortocerad")) {
    grupos.push("Orthocerida");
  }

  // Goniatitida (NUEVO)
  if (t.includes("goniatit") || t.includes("goniat")) {
    grupos.push("Goniatitida");
  }

  // Gastrópodos
  if (t.includes("gastropod") || t.includes("caracol") || t.includes("gastro")) {
    grupos.push("Gastropoda");
  }

  // Bivalvos / Ostras
  if (t.includes("bivalv") || t.includes("ostra") || t.includes("rudista")) {
    grupos.push("Bivalvia");
  }

  // Corales
  if (t.includes("coral")) {
    grupos.push("Corales");
  }

  // Nummulites / Foraminíferos
  if (t.includes("nummulit") || t.includes("foramin")) {
    grupos.push("Nummulites");
  }

  // Belemnites
  if (t.includes("belemn") || t.includes("belemno")) {
    grupos.push("Belemnites");
  }
  
  // Equinodermos (Erizos, Estrellas, Dólares de arena, Crinoideos, etc.)
  if (
    t.includes("erizo") || t.includes("estrella") || t.includes("dolar") || 
    t.includes("echino") || t.includes("astero") || t.includes("ophiuro") || 
    t.includes("crino") || t.includes("equinodermo")
  ) {
    grupos.push("Equinodermos");
  }

  // Braquiópodos
  if (t.includes("brachiopod") || t.includes("braquiopod")) {
    grupos.push("Brachiopoda");
  }

  // Trazas fósiles
  if (t.includes("traza") || t.includes("cruziana")) {
    grupos.push("Trazas fósiles");
  }

  // Si no coincidió con ninguna categoría anterior
  if (grupos.length === 0) {
    grupos.push("Otros");
  }

  return grupos;
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
      organismosGrupos: normalizarOrganismos(f.organismo),
      autor: f.autor ? f.autor.trim() : "Anónimo"
    };

    todosLosMarcadores.push(marker);
    cluster.addLayer(marker);
  });

  map.addLayer(cluster);

  // Encuadra la vista para abarcar todos los registros cargados con un margen de protección
  if (fosiles.length > 0) {
    const bounds = L.latLngBounds(fosiles.map(f => [f.lat, f.lng]));
    map.fitBounds(bounds, { padding: [40, 40] });
  }

  poblarSelects();
}

// --- 4. OPCIONES DE FILTROS ---
function poblarSelects() {
  const selectOrg = document.getElementById("filtro-organismo");
  const selectAut = document.getElementById("filtro-autor");

  selectOrg.innerHTML = '<option value="todos">Todos los organismos</option>';
  selectAut.innerHTML = '<option value="todos">Todos los autores</option>';

  // Extraer todos los grupos asignados a cada registro sin duplicados
  const todosLosGrupos = todosLosMarcadores.flatMap(m => m.datosFosil.organismosGrupos);
  const organismosUnicos = [...new Set(todosLosGrupos)].sort();
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
    // Un marcador cumple si el filtro es 'todos' o si la categoría elegida está en su lista de grupos
    const cumpleOrg = (orgSel === "todos" || m.datosFosil.organismosGrupos.includes(orgSel));
    const cumpleAut = (autSel === "todos" || m.datosFosil.autor === autSel);

    if (cumpleOrg && cumpleAut) {
      cluster.addLayer(m);
    }
  });
}

// Escuchadores de eventos para los filtros de selección
document.getElementById("filtro-organismo").addEventListener("change", aplicarFiltros);
document.getElementById("filtro-autor").addEventListener("change", aplicarFiltros);

// --- CONTROL DEL BOTÓN COMPACTO 🔍 Y CIERRE AL HACER CLIC FUERA ---
const toggleBtn = document.getElementById("toggle-panel");
const contenidoFiltros = document.getElementById("contenido-filtros");
const panelFiltros = document.getElementById("panel-filtros");

// 1. Cambia el texto del botón para que muestre únicamente la lupa
toggleBtn.innerHTML = "🔍";
toggleBtn.setAttribute("title", "Filtrar Fósiles");

// 2. Abre y cierra el menú al hacer clic en el botón de la lupa
toggleBtn.addEventListener("click", (e) => {
  e.stopPropagation(); // Evita que el clic toque el mapa
  contenidoFiltros.classList.toggle("oculto");
});

// 3. Evita que hacer clic dentro del menú desplegable cierre el panel
panelFiltros.addEventListener("click", (e) => {
  e.stopPropagation();
});

// 4. Cierra el menú automáticamente si hacés clic en cualquier parte fuera de él
document.addEventListener("click", (e) => {
  if (!panelFiltros.contains(e.target)) {
    contenidoFiltros.classList.add("oculto");
  }
});

// Inicializar
cargarPuntos();
