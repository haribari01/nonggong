// 지도 설정
const MAP_CENTER = [36.5, 127.8]; // 대한민국 중심 좌표
const MAP_ZOOM = 7;

let map = null;

// 지도 초기화 함수
function initMap() {
  // Leaflet 지도 생성
  map = L.map("map").setView(MAP_CENTER, MAP_ZOOM);

  // OpenStreetMap 타일 레이어 추가
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(map);

  // 테스트용 마커 추가 (서울)
  L.marker([37.5665, 126.9780])
    .addTo(map)
    .bindPopup("서울특별시")
    .openPopup();

  console.log("지도가 성공적으로 로드되었습니다!");
}

// DOM이 로드된 후 지도 초기화
document.addEventListener("DOMContentLoaded", function() {
  initMap();
});