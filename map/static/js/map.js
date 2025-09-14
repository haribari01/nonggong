const map = L.map('map').setView([36.5, 127.5], 7);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19
}).addTo(map);

let geoJsonLayer;
let soilData;
let currentDataType = 'high_Suit_Area';
let currentColorRanges = [];

function getColorRanges(dataType, data) {
    const values = data.map(d => d[dataType]).filter(v => v > 0).sort((a, b) => b - a);
    if (values.length === 0) return [
        { min: 0, color: 'rgb(240, 240, 240)' }
    ];

    const max = Math.max(...values);

    return [
        { min: max * 0.8, color: 'rgb(34, 139, 34)' },      // 진한 초록 (80%+)
        { min: max * 0.6, color: 'rgb(144, 238, 144)' },    // 연한 초록 (60-80%)
        { min: max * 0.4, color: 'rgb(255, 241, 118)' },    // 노랑 (40-60%)
        { min: max * 0.2, color: 'rgb(255, 193, 144)' },    // 주황 (20-40%)
        { min: 1, color: 'rgb(255, 69, 0)' },            // 진한 주황 (1-20%)
        { min: 0, color: 'rgb(240, 240, 240)' }             // 회색 (0)
    ];
}

function getColor(value, ranges) {
    if (value === 0) return 'rgb(240, 240, 240)';

    for (let range of ranges) {
        if (value >= range.min) {
            return range.color;
        }
    }
    return 'rgb(255, 235, 235)';
}

function style(feature, dataType, ranges) {
    const ctprvn_cd = feature.properties.CTPRVN_CD;
    const data = soilData.find(d => d.ctprvn_cd === ctprvn_cd);
    const value = data ? data[dataType] : 0;

    return {
        fillColor: getColor(value, ranges),
        weight: 1,
        opacity: 1,
        color: '#666',
        fillOpacity: 0.8
    };
}

function highlightFeature(e) {
    const layer = e.target;
    layer.setStyle({
        weight: 3,
        color: '#fff',
        fillOpacity: 0.9
    });
    layer.bringToFront();
}

function resetHighlight(e) {
    geoJsonLayer.resetStyle(e.target);
}

function updateLegend(dataType, ranges) {
    const legendItems = document.getElementById('legendItems');
    const selectedText = document.querySelector(`#dataSelector option[value="${dataType}"]`).textContent;

    document.querySelector('.legend-title').textContent = `${selectedText} (ha)`;

    legendItems.innerHTML = '';

    ranges.forEach((range, index) => {
        const item = document.createElement('div');
        item.className = 'legend-item';

        const colorBox = document.createElement('div');
        colorBox.className = 'legend-color';
        colorBox.style.backgroundColor = range.color;

        const label = document.createElement('span');
        if (range.min === 0) {
            label.textContent = `0 (없음)`;
        } else if (index === 0) {
            label.textContent = `${Math.round(range.min).toLocaleString()}+`;
        } else {
            const nextMin = ranges[index-1].min;
            label.textContent = `${Math.round(range.min).toLocaleString()} - ${Math.round(nextMin - 1).toLocaleString()}`;
        }

        item.appendChild(colorBox);
        item.appendChild(label);
        legendItems.appendChild(item);
    });
}

function updateMap() {
    if (geoJsonLayer) {
        map.removeLayer(geoJsonLayer);
    }

    Promise.all([
        fetch('/static/data/sido_wgs84.json').then(response => response.json()),
        fetch('/api/soil-data').then(response => response.json())
    ]).then(([geoData, data]) => {
        soilData = data;
        currentColorRanges = getColorRanges(currentDataType, data);

        geoJsonLayer = L.geoJSON(geoData, {
            style: function(feature) {
                return style(feature, currentDataType, currentColorRanges);
            },
            onEachFeature: function(feature, layer) {
                const ctprvn_cd = feature.properties.CTPRVN_CD;
                const regionData = soilData.find(d => d.ctprvn_cd === ctprvn_cd);
                const regionName = feature.properties.CTP_KOR_NM;

                if (regionData) {
                    const totalArea = regionData.high_Suit_Area + regionData.suit_Area + regionData.poss_Area + regionData.low_Suit_Area + regionData.etc_Area;

                    layer.bindPopup(`
                        <div style="font-family: 'Malgun Gothic', Arial, sans-serif; min-width: 200px; padding: 8px;">
                            <div style="font-weight: bold; font-size: 15px; margin-bottom: 10px; color: #333; text-align: center;">${regionName}</div>
                            <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                                <tr style="border-bottom: 1px solid #eee;">
                                    <td style="padding: 3px 0; color: #666; width: 60%;">최적지 면적:</td>
                                    <td style="padding: 3px 0; color: #4A90E2; font-weight: bold; text-align: right;">${regionData.high_Suit_Area.toLocaleString()}</td>
                                    <td style="padding: 3px 0; color: #999; text-align: right; font-size: 11px; width: 15%;">ha</td>
                                </tr>
                                <tr style="border-bottom: 1px solid #eee;">
                                    <td style="padding: 3px 0; color: #666;">적지:</td>
                                    <td style="padding: 3px 0; color: #4A90E2; font-weight: bold; text-align: right;">${regionData.suit_Area.toLocaleString()}</td>
                                    <td style="padding: 3px 0; color: #999; text-align: right; font-size: 11px;">ha</td>
                                </tr>
                                <tr style="border-bottom: 1px solid #eee;">
                                    <td style="padding: 3px 0; color: #666;">가능지:</td>
                                    <td style="padding: 3px 0; color: #4A90E2; font-weight: bold; text-align: right;">${regionData.poss_Area.toLocaleString()}</td>
                                    <td style="padding: 3px 0; color: #999; text-align: right; font-size: 11px;">ha</td>
                                </tr>
                                <tr style="border-bottom: 1px solid #eee;">
                                    <td style="padding: 3px 0; color: #666;">저위생산지:</td>
                                    <td style="padding: 3px 0; color: #4A90E2; font-weight: bold; text-align: right;">${regionData.low_Suit_Area.toLocaleString()}</td>
                                    <td style="padding: 3px 0; color: #999; text-align: right; font-size: 11px;">ha</td>
                                </tr>
                                <tr>
                                    <td style="padding: 3px 0; color: #666;">기타:</td>
                                    <td style="padding: 3px 0; color: #4A90E2; font-weight: bold; text-align: right;">${regionData.etc_Area.toLocaleString()}</td>
                                    <td style="padding: 3px 0; color: #999; text-align: right; font-size: 11px;">ha</td>
                                </tr>
                            </table>
                            <div style="margin-top: 8px; padding-top: 6px; border-top: 2px solid #ddd; text-align: center;">
                                <span style="color: #666; font-size: 12px;">전체 면적: </span>
                                <span style="color: #333; font-weight: bold; font-size: 13px;">${totalArea.toLocaleString()}</span>
                                <span style="color: #999; font-size: 11px;"> ha</span>
                            </div>
                        </div>
                    `, {
                        maxWidth: 220,
                        className: 'custom-popup'
                    });
                } else {
                    layer.bindPopup(`<div style="font-family: Arial, sans-serif;"><strong>${regionName}</strong><br/>데이터 없음</div>`);
                }

                layer.on({
                    mouseover: highlightFeature,
                    mouseout: resetHighlight
                });
            }
        }).addTo(map);

        updateLegend(currentDataType, currentColorRanges);
    }).catch(error => {
        console.error('데이터 로드 실패:', error);
    });
}

document.getElementById('dataSelector').addEventListener('change', function(e) {
    currentDataType = e.target.value;
    updateMap();
});

updateMap();