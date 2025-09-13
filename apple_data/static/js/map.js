// 지도 설정
const MAP_CENTER = [36.5, 127.8]; // 대한민국 중심 좌표
const MAP_ZOOM = 7;

// 줌 레벨별 행정구역 설정
const ZOOM_LEVELS = {
  SIDO: { min: 0, max: 7, file: "/static/data/sido_wgs84.json" },
  SIGUNGU: { min: 8, max: 8, file: "/static/data/si_gun_gu_wgs84.json" },
  EUPMYEONDONG: { min: 9, max: 9, file: "/static/data/eup_myeon_dong_wgs84.json" },
  LI: { min: 10, max: 18, file: "/static/data/li_wgs84.json" }
};

let map = null;
let currentBoundaryLayer = null;
let currentLevel = null;
let boundaryCache = {}; // GeoJSON 캐시

// GeoJSON 파일 로드 함수
async function loadGeoJSON(url) {
  if (boundaryCache[url]) {
    return boundaryCache[url];
  }

  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const geojson = await response.json();
    boundaryCache[url] = geojson;
    return geojson;
  } catch (error) {
    console.error(`GeoJSON 로드 실패 (${url}):`, error);
    return null;
  }
}

// 현재 줌 레벨에 맞는 행정구역 레벨 결정
function getCurrentLevel(zoom) {
  for (const [level, config] of Object.entries(ZOOM_LEVELS)) {
    if (zoom >= config.min && zoom <= config.max) {
      return level;
    }
  }
  return 'SIDO'; // 기본값
}

// 경계선 스타일 설정
function getBoundaryStyle(level) {
  const styles = {
    SIDO: {
      weight: 3,
      color: '#ff0000',
      fillColor: '#ffcccc',
      fillOpacity: 0.3,
      dashArray: null
    },
    SIGUNGU: {
      weight: 2,
      color: '#0066cc',
      fillColor: '#cce6ff',
      fillOpacity: 0.2,
      dashArray: null
    },
    EUPMYEONDONG: {
      weight: 1.5,
      color: '#00aa00',
      fillColor: '#ccffcc',
      fillOpacity: 0.1,
      dashArray: '5, 5'
    },
    LI: {
      weight: 1,
      color: '#8b4513',
      fillColor: '#f4e4bc',
      fillOpacity: 0.05,
      dashArray: '3, 3'
    }
  };

  return styles[level] || styles.SIDO;
}

// 팝업 내용 생성
function createPopupContent(properties, level) {
  let name = '';
  let code = '';

  switch (level) {
    case 'SIDO':
      name = properties.CTP_KOR_NM || properties.CTPRVN_NM || '정보 없음';
      code = properties.CTPRVN_CD || properties.CTP_CD || '';
      break;
    case 'SIGUNGU':
      name = properties.SIG_KOR_NM || properties.SIGUNGU_NM || '정보 없음';
      code = properties.SIG_CD || properties.SIGUNGU_CD || '';
      break;
    case 'EUPMYEONDONG':
      name = properties.EMD_KOR_NM || properties.DONG_NM || '정보 없음';
      code = properties.EMD_CD || properties.DONG_CD || '';
      break;
    case 'LI':
      name = properties.LI_KOR_NM || properties.RI_NM || '정보 없음';
      code = properties.LI_CD || properties.RI_CD || '';
      break;
  }

  return `
    <div style="font-size: 14px; line-height: 1.4;">
      <strong>${name}</strong><br>
      <span style="font-size: 12px; color: #666;">
        ${level} (${code})
      </span>
    </div>
  `;
}

// 경계선 레이어 업데이트
async function updateBoundaryLayer() {
  const currentZoom = map.getZoom();
  const newLevel = getCurrentLevel(currentZoom);

  // 레벨이 변경되지 않았으면 업데이트하지 않음
  if (newLevel === currentLevel && currentBoundaryLayer) {
    return;
  }

  // 기존 레이어 제거
  if (currentBoundaryLayer) {
    map.removeLayer(currentBoundaryLayer);
    currentBoundaryLayer = null;
  }

  // 새 GeoJSON 로드 및 레이어 추가
  const config = ZOOM_LEVELS[newLevel];
  const geojson = await loadGeoJSON(config.file);

  if (geojson) {
    const style = getBoundaryStyle(newLevel);

    currentBoundaryLayer = L.geoJSON(geojson, {
      style: style,
      onEachFeature: (feature, layer) => {
        // 팝업 설정
        const popupContent = createPopupContent(feature.properties, newLevel);
        layer.bindPopup(popupContent);

        // 마우스 이벤트
        layer.on({
          mouseover: (e) => {
            const layer = e.target;
            layer.setStyle({
              weight: style.weight + 1,
              color: '#000000',
              fillOpacity: style.fillOpacity + 0.2
            });
            layer.bringToFront();
          },
          mouseout: (e) => {
            currentBoundaryLayer.resetStyle(e.target);
          }
        });
      }
    }).addTo(map);

    currentLevel = newLevel;
    console.log(`${newLevel} 경계선 로드 완료 (줌 레벨: ${currentZoom})`);
  }
}

// 지도 초기화 함수
async function initMap() {
  // Leaflet 지도 생성
  map = L.map("map").setView(MAP_CENTER, MAP_ZOOM);

  // OpenStreetMap 타일 레이어 추가
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 18
  }).addTo(map);

  // 줌 이벤트 리스너 추가
  map.on('zoomend', updateBoundaryLayer);

  // 초기 경계선 로드
  await updateBoundaryLayer();

  console.log("지도가 성공적으로 로드되었습니다!");
}

// DOM이 로드된 후 지도 초기화
document.addEventListener("DOMContentLoaded", function() {
  initMap();
});