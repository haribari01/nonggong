// 전역 변수
let leafletMap;
let mapLayer;
let mapData = [];
let selectedFile = '';
let selectedCrop = '';
let selectedDataType = 'high_Suit_Area';
let colorScale = [];
let currentLevel = 'sido';

// 줌 레벨별 행정구역 설정
const ZOOM_LEVELS = {
    SIDO: { min: 0, max: 7, file: "/static/data/sido_wgs84.json", level: 'sido', idField: 'CTPRVN_CD' },
    SIGUNGU: { min: 8, max: 8, file: "/static/data/si_gun_gu_wgs84.json", level: 'sigungu', idField: 'SIG_CD' },
    EUPMYEONDONG: { min: 9, max: 9, file: "/static/data/eup_myeon_dong_wgs84.json", level: 'eupmyeondong', idField: 'EMD_CD' },
    LI: { min: 10, max: 18, file: "/static/data/li_wgs84.json", level: 'li', idField: 'LI_CD' }
};

// 지도 초기화
function initializeMap() {
    leafletMap = L.map('mapContainer').setView([36.5, 127.5], 7);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 18
    }).addTo(leafletMap);

    // 줌 이벤트 리스너 추가
    leafletMap.on('zoomend', handleZoomChange);
}

// 줌 레벨에 따른 행정구역 레벨 결정
function getCurrentLevelConfig(zoomLevel) {
    for (const config of Object.values(ZOOM_LEVELS)) {
        if (zoomLevel >= config.min && zoomLevel <= config.max) {
            return config;
        }
    }
    return ZOOM_LEVELS.SIDO; // 기본값
}

// 줌 변경 처리
function handleZoomChange() {
    const currentZoom = leafletMap.getZoom();
    const levelConfig = getCurrentLevelConfig(currentZoom);

    if (currentLevel !== levelConfig.level) {
        currentLevel = levelConfig.level;
        renderMapData();
    }
}

// 색상 스케일 계산 (레벨별로 동적 계산)
function calculateColorScale(dataType, data, level) {
    const validValues = data.map(d => d[dataType]).filter(v => v > 0).sort((a, b) => b - a);

    if (validValues.length === 0) {
        return [{ min: 0, color: 'rgb(240, 240, 240)' }];
    }

    const maxValue = Math.max(...validValues);

    // 레벨별로 스케일 조정
    const scaleRatios = {
        'sido': [0.8, 0.6, 0.4, 0.2],
        'sigungu': [0.1, 0.075, 0.05, 0.025],
        'eupmyeondong': [0.01, 0.006, 0.003, 0.001],
        'li': [0.001, 0.0006, 0.0003, 0.0002]
    }[level];

    return [
        { min: maxValue * scaleRatios[0], color: 'rgb(34, 139, 34)' },     // 진한 초록
        { min: maxValue * scaleRatios[1], color: 'rgb(144, 238, 144)' },   // 연한 초록
        { min: maxValue * scaleRatios[2], color: 'rgb(255, 241, 118)' },   // 노랑
        { min: maxValue * scaleRatios[3], color: 'rgb(255, 193, 144)' },   // 주황
        { min: 1, color: 'rgb(255, 69, 0)' },                             // 진한 주황
        { min: 0, color: 'rgb(240, 240, 240)' }                           // 회색
    ];
}

// 값에 따른 색상 반환
function getValueColor(value, scale) {
    if (value === 0) return 'rgb(240, 240, 240)';

    for (const range of scale) {
        if (value >= range.min) {
            return range.color;
        }
    }
    return 'rgb(220, 20, 20)';
}

// 지역 스타일 설정
function getRegionStyle(feature, levelConfig) {
    const regionCode = feature.properties[levelConfig.idField];
    const regionInfo = mapData.find(d => d.region_cd === regionCode);
    const value = regionInfo ? regionInfo[selectedDataType] : 0;

    return {
        fillColor: getValueColor(value, colorScale),
        weight: 1,
        opacity: 1,
        color: '#666',
        fillOpacity: 0.8
    };
}

// 마우스 호버 효과
function highlightRegion(e) {
    const layer = e.target;
    layer.setStyle({
        weight: 3,
        color: '#ffffff',
        fillOpacity: 0.9
    });
    layer.bringToFront();
}

function resetRegionStyle(e) {
    if (mapLayer) {
        mapLayer.resetStyle(e.target);
    }
}

// 팝업 생성
function createPopupContent(feature, levelConfig) {
    const regionCode = feature.properties[levelConfig.idField];
    const regionInfo = mapData.find(d => d.region_cd === regionCode);

    const regionName = {
        'sido': () => feature.properties.CTP_KOR_NM,
        'sigungu': () => feature.properties.SIG_KOR_NM,
        'eupmyeondong': () => feature.properties.EMD_KOR_NM,
        'li': () => feature.properties.LI_KOR_NM
    }[levelConfig.level]() || regionCode;

    if (!regionInfo) {
        return `<div style="font-family: 'Malgun Gothic', Arial; padding: 10px;"><strong>${regionName}</strong><br>데이터 없음</div>`;
    }

    const totalArea = regionInfo.high_Suit_Area + regionInfo.suit_Area + regionInfo.poss_Area + regionInfo.low_Suit_Area + regionInfo.etc_Area;

    return `
        <div style="font-family: 'Malgun Gothic', Arial; min-width: 200px; padding: 10px;">
            <div style="font-weight: bold; font-size: 16px; margin-bottom: 8px; text-align: center; color: #333;">${regionName}</div>
            <div style="font-size: 13px; margin-bottom: 10px; text-align: center; color: #666;">${regionInfo.soil_Crop_Nm}</div>
            <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 4px 0; color: #666;">최적지 면적:</td>
                    <td style="padding: 4px 0; color: #2196F3; font-weight: bold; text-align: right;">${regionInfo.high_Suit_Area.toLocaleString()}</td>
                    <td style="padding: 4px 0; color: #999; font-size: 12px; text-align: right;">ha</td>
                </tr>
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 4px 0; color: #666;">적지:</td>
                    <td style="padding: 4px 0; color: #2196F3; font-weight: bold; text-align: right;">${regionInfo.suit_Area.toLocaleString()}</td>
                    <td style="padding: 4px 0; color: #999; font-size: 12px; text-align: right;">ha</td>
                </tr>
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 4px 0; color: #666;">가능지:</td>
                    <td style="padding: 4px 0; color: #2196F3; font-weight: bold; text-align: right;">${regionInfo.poss_Area.toLocaleString()}</td>
                    <td style="padding: 4px 0; color: #999; font-size: 12px; text-align: right;">ha</td>
                </tr>
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 4px 0; color: #666;">저위생산지:</td>
                    <td style="padding: 4px 0; color: #2196F3; font-weight: bold; text-align: right;">${regionInfo.low_Suit_Area.toLocaleString()}</td>
                    <td style="padding: 4px 0; color: #999; font-size: 12px; text-align: right;">ha</td>
                </tr>
                <tr>
                    <td style="padding: 4px 0; color: #666;">기타:</td>
                    <td style="padding: 4px 0; color: #2196F3; font-weight: bold; text-align: right;">${regionInfo.etc_Area.toLocaleString()}</td>
                    <td style="padding: 4px 0; color: #999; font-size: 12px; text-align: right;">ha</td>
                </tr>
            </table>
            <div style="margin-top: 10px; padding-top: 8px; border-top: 2px solid #ddd; text-align: center;">
                <span style="color: #666; font-size: 13px;">전체 면적: </span>
                <span style="color: #333; font-weight: bold; font-size: 14px;">${totalArea.toLocaleString()}</span>
                <span style="color: #999; font-size: 12px;"> ha</span>
            </div>
        </div>
    `;
}

// 범례 업데이트
function updateMapLegend() {
    const dataNames = {
        'high_Suit_Area': '최적지_면적',
        'suit_Area': '적지_면적',
        'poss_Area': '가능지_면적',
        'low_Suit_Area': '저위생산지_면적',
        'etc_Area': '기타_면적'
    };

    const levelNames = {
        'sido': '시도',
        'sigungu': '시군구',
        'eupmyeondong': '읍면동',
        'li': '리'
    };

    document.getElementById('legendTitle').textContent = `${dataNames[selectedDataType]} (${levelNames[currentLevel]})`;

    const legendContent = document.getElementById('legendContent');
    legendContent.innerHTML = '';

    colorScale.forEach((range, index) => {
        const item = document.createElement('div');
        item.className = 'legend-item';

        const colorBox = document.createElement('div');
        colorBox.className = 'legend-color-box';
        colorBox.style.backgroundColor = range.color;

        const label = document.createElement('span');
        if (range.min === 0) {
            label.textContent = '0 (없음)';
        } else if (index === 0) {
            label.textContent = `${Math.round(range.min).toLocaleString()}+`;
        } else {
            const prevMin = colorScale[index-1].min;
            label.textContent = `${Math.round(range.min).toLocaleString()} - ${Math.round(prevMin - 1).toLocaleString()}`;
        }

        item.appendChild(colorBox);
        item.appendChild(label);
        legendContent.appendChild(item);
    });
}

// 지도 데이터 렌더링
function renderMapData() {
    if (!selectedFile || !selectedCrop) {
        if (mapLayer) {
            leafletMap.removeLayer(mapLayer);
        }
        document.getElementById('legendBox').style.display = 'none';
        return;
    }

    const levelConfig = getCurrentLevelConfig(leafletMap.getZoom());
    currentLevel = levelConfig.level;

    Promise.all([
        fetch(levelConfig.file).then(r => r.json()),
        fetch(`/api/data?filename=${selectedFile}&crop_code=${selectedCrop}&level=${currentLevel}`).then(r => r.json())
    ]).then(([geoData, data]) => {
        mapData = data;
        colorScale = calculateColorScale(selectedDataType, data, currentLevel);

        if (mapLayer) {
            leafletMap.removeLayer(mapLayer);
        }

        mapLayer = L.geoJSON(geoData, {
            style: function(feature) {
                return getRegionStyle(feature, levelConfig);
            },
            onEachFeature: function(feature, layer) {
                layer.bindPopup(createPopupContent(feature, levelConfig), {
                    maxWidth: 250,
                    className: 'custom-popup'
                });

                layer.on({
                    mouseover: highlightRegion,
                    mouseout: resetRegionStyle
                });
            }
        }).addTo(leafletMap);

        updateMapLegend();
        document.getElementById('legendBox').style.display = 'block';

    }).catch(err => {
        console.error('데이터 로드 오류:', err);
    });
}

// 초기화 및 이벤트 설정
document.addEventListener('DOMContentLoaded', function() {
    initializeMap();

    // CSV 파일 목록 로드
    fetch('/api/csv-list')
        .then(r => r.json())
        .then(files => {
            const csvSelect = document.getElementById('csvSelect');
            files.forEach(file => {
                const option = document.createElement('option');
                option.value = file.filename;
                option.textContent = file.display_name;
                csvSelect.appendChild(option);
            });
        });

    // CSV 선택 이벤트
    document.getElementById('csvSelect').addEventListener('change', function(e) {
        selectedFile = e.target.value;
        const cropSelect = document.getElementById('cropSelect');
        const dataSelect = document.getElementById('dataSelect');

        if (selectedFile) {
            // 제목 표시
            const titleText = e.target.options[e.target.selectedIndex].textContent;
            document.getElementById('titleText').textContent = titleText;
            document.getElementById('titleContainer').style.display = 'block';

            // 작물 목록 로드
            fetch(`/api/crops?filename=${selectedFile}`)
                .then(r => r.json())
                .then(crops => {
                    cropSelect.innerHTML = '<option value="">선택하세요</option>';
                    crops.forEach(crop => {
                        const option = document.createElement('option');
                        option.value = crop.soil_Crop_Cd;
                        option.textContent = crop.soil_Crop_Nm;
                        cropSelect.appendChild(option);
                    });
                    cropSelect.disabled = false;

                    // 사과 기본 선택
                    const appleOption = Array.from(cropSelect.options).find(opt => opt.value === 'CR005');
                    if (appleOption) {
                        appleOption.selected = true;
                        selectedCrop = 'CR005';
                        dataSelect.disabled = false;
                        renderMapData();
                    }
                });
        } else {
            // 초기화
            document.getElementById('titleContainer').style.display = 'none';
            cropSelect.innerHTML = '<option value="">선택하세요</option>';
            cropSelect.disabled = true;
            dataSelect.disabled = true;
            selectedFile = '';
            selectedCrop = '';
            renderMapData();
        }
    });

    // 작물 선택 이벤트
    document.getElementById('cropSelect').addEventListener('change', function(e) {
        selectedCrop = e.target.value;
        const dataSelect = document.getElementById('dataSelect');

        if (selectedCrop) {
            dataSelect.disabled = false;
            renderMapData();
        } else {
            dataSelect.disabled = true;
            renderMapData();
        }
    });

    // 데이터 타입 선택 이벤트
    document.getElementById('dataSelect').addEventListener('change', function(e) {
        selectedDataType = e.target.value;
        if (selectedFile && selectedCrop) {
            renderMapData();
        }
    });
});