from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(title="Soil Suitability Map")

# 디렉토리 설정
BASE_DIR = os.path.abspath(os.getcwd())
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# 루트 경로와 api/soil 둘 다 지도로 연결
@app.get("/", response_class=FileResponse)
@app.get("/api/soil", response_class=FileResponse)
def get_soil_map():
    """토양 적합성 지도 페이지 반환"""
    index_path = os.path.join(TEMPLATES_DIR, "index.html")
    if not os.path.exists(index_path):
        return {"error": "index.html not found"}
    return FileResponse(index_path, media_type="text/html")

# 정적 파일 서빙 (CSS, JS)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)