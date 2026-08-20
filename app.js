// Centro inicial del mapa (Argentina)
const map = L.map('map').setView([-34.6, -64.0], 5);

// Capa base de OpenStreetMap
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> colaboradores',
  maxZoom: 19
}).addTo(map);

// Icono personalizado
const fosilIcon = L.divIcon({
  className: '',
  html: '<div class="fosil-icon">🦴</div>',
  iconSize: [26, 26],
  iconAnchor: [13, 13],
  popupAnchor: [0, -13]
});

// Agrupador de marcadores (para que no se amontonen al alejar el zoom)
const cluster = L.markerClusterGroup();

fosiles.forEach(f => {
  const marker = L.marker([f.lat, f.lng], { icon: fosilIcon });

  const fotosHtml = f.fotos.length
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
  cluster.addLayer(marker);
});

map.addLayer(cluster);

// Ajustar el zoom para que se vean todos los puntos
if (fosiles.length > 0) {
  const bounds = L.latLngBounds(fosiles.map(f => [f.lat, f.lng]));
  map.fitBounds(bounds, { padding: [30, 30] });
}
