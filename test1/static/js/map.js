// ==================== 전역 변수 ====================
const GEO_URL = "/static/data/Si_Gun_Gu.json";
const MAP_CENTER = [36.5, 127.8];
const MAP_ZOOM = 7;

let map = null;
let geoLayer = null;
let legend = null;
let geojson = null;
let currentData = [];
let currentCrop = null;

// DOM 요소
const titleEl = document.getElementById("title");
const subtitleEl = document.getElementById("subtitle");
const cropSelect = document.getElementById("cropSelect");
const viewModeSelect = document.getElementById("viewMode");
const loadingEl = document.getElementById("loading");

// ==================== 유틸리티 함수 ====================

function showLoading() {
  loadingEl.classList.remove("hidden");
}

function hideLoading() {
  loadingEl.classList.add("hidden");
}

function normalizeRegionName(name) {
  if (!name) return "";
  const cleanName = name.trim();

  // "시도 + 시군구" 형태에서 시군구만 추출
  const parts = cleanName.split(" ");
  if (parts.length >= 2) {
    return parts[parts.length - 1]; // 마지막 부분 (시군구)
  }
  return cleanName;
}

function stripLastUnit(korName) {
  if (!korName) return "";
  const nm = String(korName).trim();
  const last = nm.slice(-1);
  if (["시", "군", "구"].includes(last)) return nm.slice(0, -1);
  return nm;
}

function getColor(value, mode, minVal, maxVal) {
  if (value === null || value === undefined || isNaN(value)) {
    return "#e9ecef";
  }

  // 값을 0-1 범위로 정규화
  let normalizedValue;
  if (maxVal === minVal) {
    normalizedValue = 0.5;
  } else {
    normalizedValue = (value - minVal) / (maxVal - minVal);
  }

  // 색상 팔레트 (낮음 -> 높음)
  const colorStops = [
    { pos: 0, color: [255, 235, 235] },    // 연한 빨강 (낮음)
    { pos: 0.25, color: [255, 193, 144] }, // 주황
    { pos: 0.5, color: [255, 241, 118] },  // 노랑
    { pos: 0.75, color: [144, 238, 144] }, // 연한 초록
    { pos: 1, color: [34, 139, 34] }       // 진한 초록 (높음)
  ];

  // 적합성 점수의 경우 더 세밀한 그라데이션
  if (mode === 'suitability') {
    // 적합성 점수는 0-4 범위이므로 특별 처리
    normalizedValue = Math.min(Math.max(normalizedValue, 0), 1);
  }

  // 색상 보간
  for (let i = 0; i < colorStops.length - 1; i++) {
    if (normalizedValue >= colorStops[i].pos && normalizedValue <= colorStops[i + 1].pos) {
      const ratio = (normalizedValue - colorStops[i].pos) / (colorStops[i + 1].pos - colorStops[i].pos);
      const r = Math.round(colorStops[i].color[0] + ratio * (colorStops[i + 1].color[0] - colorStops[i].color[0]));
      const g = Math.round(colorStops[i].color[1] + ratio * (colorStops[i + 1].color[1] - colorStops[i].color[1]));
      const b = Math.round(colorStops[i].color[2] + ratio * (colorStops[i + 1].color[2] - colorStops[i].color[2]));
      return `rgb(${r}, ${g}, ${b})`;
    }
  }

  return "#e9ecef";
}

function formatNumber(num) {
  if (num === null || num === undefined) return "N/A";
  if (typeof num === 'number') {
    return num.toLocaleString();
  }
  return num;
}

// ==================== API 함수 ====================

async function loadCrops() {
  try {
    const response = await fetch("/api/crops");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const crops = await response.json();

    cropSelect.innerHTML = '<option value="">작물을 선택하세요...</option>';
    crops.forEach(crop => {
      const option = document.createElement("option");
      option.value = crop.code;
      option.textContent = crop.name;
      cropSelect.appendChild(option);
    });
  } catch (error) {
    console.error("작물 목록 로드 실패:", error);
    alert("작물 목록을 불러오는데 실패했습니다.");
  }
}

async function loadSuitabilityData(cropCode) {
  try {
    showLoading();
    const response = await fetch(`/api/suitability?crop_code=${encodeURIComponent(cropCode)}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();

    currentData = data;
    return data;
  } catch (error) {
    console.error("적합성 데이터 로드 실패:", error);
    alert("데이터를 불러오는데 실패했습니다.");
    return [];
  } finally {
    hideLoading();
  }
}

async function loadGeoJSON() {
  try {
    const response = await fetch(GEO_URL);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    geojson = await response.json();
  } catch (error) {
    console.error("GeoJSON 로드 실패:", error);
    alert("지도 데이터를 불러오는데 실패했습니다.");
  }
}

// ==================== 지도 렌더링 ====================

function createDataMap(data, mode) {
  const dataMap = new Map();

  data.forEach(item => {
    const regionName = normalizeRegionName(item.region_name);
    const key = stripLastUnit(regionName);

    let value;
    switch (mode) {
      case 'suitability':
        value = item.suitability_score;
        break;
      case 'high_suit':
        value = item.high_suit_area;
        break;
      case 'total_area':
        value = item.total_area;
        break;
      default:
        value = item.suitability_score;
    }

    dataMap.set(key, {
      value: value,
      data: item
    });
  });

  return dataMap;
}

function calculateMinMax(data, mode) {
  const values = data.map(item => {
    switch (mode) {
      case 'suitability':
        return item.suitability_score;
      case 'high_suit':
        return item.high_suit_area;
      case 'total_area':
        return item.total_area;
      default:
        return item.suitability_score;
    }
  }).filter(v => v !== null && v !== undefined && !isNaN(v));

  if (values.length === 0) return { min: 0, max: 1 };

  return {
    min: Math.min(...values),
    max: Math.max(...values)
  };
}

function getStyleForFeature(feature, dataMap, mode, minVal, maxVal) {
  const geoName = stripLastUnit(feature.properties.SIG_KOR_NM);
  const dataItem = dataMap.get(geoName);

  if (!dataItem) {
    return {
      weight: 1,
      color: "#999",
      fillColor: "#e9ecef",
      fillOpacity: 0.7
    };
  }

  const fillColor = getColor(dataItem.value, mode, minVal, maxVal);

  return {
    weight: 1.5,
    color: "#666",
    fillColor: fillColor,
    fillOpacity: 0.8
  };
}

function createPopupContent(regionName, dataItem, mode) {
  if (!dataItem) {
    return `
      <div class="popup-title">${regionName}</div>
      <div class="popup-content">
        <div style="color: #6c757d; font-style: italic;">데이터 없음</div>
      </div>
    `;
  }

  const data = dataItem.data;

  let modeLabel;
  let modeValue;
  switch (mode) {
    case 'suitability':
      modeLabel = "적합성 점수";
      modeValue = data.suitability_score;
      break;
    case 'high_suit':
      modeLabel = "매우 적합 면적";
      modeValue = formatNumber(data.high_suit_area) + " ha";
      break;
    case 'total_area':
      modeLabel = "전체 면적";
      modeValue = formatNumber(data.total_area) + " ha";
      break;
  }

  return `
    <div class="popup-title">${regionName}</div>
    <div class="popup-content">
      <div class="popup-row">
        <span class="popup-label">${modeLabel}:</span>
        <span class="popup-value">${modeValue}</span>
      </div>
      <div class="popup-row">
        <span class="popup-label">매우 적합:</span>
        <span class="popup-value">${formatNumber(data.high_suit_area)} ha</span>
      </div>
      <div class="popup-row">
        <span class="popup-label">적합:</span>
        <span class="popup-value">${formatNumber(data.suit_area)} ha</span>
      </div>
      <div class="popup-row">
        <span class="popup-label">가능:</span>
        <span class="popup-value">${formatNumber(data.poss_area)} ha</span>
      </div>
      <div class="popup-row">
        <span class="popup-label">부적합:</span>
        <span class="popup-value">${formatNumber(data.low_suit_area)} ha</span>
      </div>
      <div class="popup-score">
        적합성 점수: ${data.suitability_score}/4.0
      </div>
    </div>
  `;
}

function updateLegend(mode, minVal, maxVal) {
  if (legend) {
    map.removeControl(legend);
  }

  legend = L.control({ position: "bottomright" });

  legend.onAdd = function() {
    const div = L.DomUtil.create("div", "legend");

    let title;
    let unit = "";
    switch (mode) {
      case 'suitability':
        title = "적합성 점수";
        unit = "/4.0";
        break;
      case 'high_suit':
        title = "매우 적합 면적";
        unit = "ha";
        break;
      case 'total_area':
        title = "전체 면적";
        unit = "ha";
        break;
    }

    div.innerHTML = `
      <h4>${title}</h4>
      <div class="legend-scale" style="background: linear-gradient(to right, 
        rgb(255,235,235), rgb(255,193,144), rgb(255,241,118), rgb(144,238,144), rgb(34,139,34));">
      </div>
      <div class="legend-labels">
        <span>${formatNumber(minVal)}${unit}</span>
        <span>${formatNumber(maxVal)}${unit}</span>
      </div>
      <div style="margin-top: 8px; font-size: 11px; color: #6c757d;">
        낮음 ← → 높음
      </div>
    `;

    return div;
  };

  legend.addTo(map);
}

async function renderMap() {
  if (!geojson || currentData.length === 0) return;

  const mode = viewModeSelect.value;
  const { min, max } = calculateMinMax(currentData, mode);
  const dataMap = createDataMap(currentData, mode);

  // 기존 레이어 제거
  if (geoLayer) {
    map.removeLayer(geoLayer);
  }

  // 새 레이어 생성
  geoLayer = L.geoJSON(geojson, {
    style: feature => getStyleForFeature(feature, dataMap, mode, min, max),
    onEachFeature: (feature, layer) => {
      const regionName = feature.properties.SIG_KOR_NM;
      const geoName = stripLastUnit(regionName);
      const dataItem = dataMap.get(geoName);

      layer.bindPopup(createPopupContent(regionName, dataItem, mode));

      // 마우스 이벤트
      layer.on({
        mouseover: (e) => {
          const layer = e.target;
          layer.setStyle({
            weight: 3,
            color: '#000',
            fillOpacity: 0.9
          });
          layer.bringToFront();
        },
        mouseout: (e) => {
          const layer = e.target;
          layer.setStyle(getStyleForFeature(feature, dataMap, mode, min, max));
        }
      });
    }
  }).addTo(map);

  // 범례 업데이트
  updateLegend(mode, min, max);
}

// ==================== 이벤트 핸들러 ====================

cropSelect.addEventListener("change", async () => {
  const cropCode = cropSelect.value;
  if (!cropCode) {
    currentData = [];
    currentCrop = null;
    subtitleEl.textContent = "";
    if (geoLayer) {
      map.removeLayer(geoLayer);
    }
    if (legend) {
      map.removeControl(legend);
    }
    return;
  }

  currentCrop = cropCode;
  const selectedOption = cropSelect.options[cropSelect.selectedIndex];
  const cropName = selectedOption.textContent;
  subtitleEl.textContent = `${cropName} 재배 적합성 분석`;

  const data = await loadSuitabilityData(cropCode);
  await renderMap();
});

viewModeSelect.addEventListener("change", () => {
  if (currentData.length > 0) {
    renderMap();
  }
});

// ==================== 초기화 ====================

async function initMap() {
  // 지도 생성
  map = L.map("map").setView(MAP_CENTER, MAP_ZOOM);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(map);

  // 데이터 로드
  await Promise.all([
    loadGeoJSON(),
    loadCrops()
  ]);

  hideLoading();
}

// 페이지 로드 시 초기화
document.addEventListener("DOMContentLoaded", () => {
  initMap();
});