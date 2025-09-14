// 지도 초기화 (한반도 전체)
const map = L.map('map').setView([36.5, 127.5], 7);

// OpenStreetMap 타일 레이어 추가
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19
}).addTo(map);