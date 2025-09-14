from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI()

# 정적 파일들을 서빙
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
@app.get("/api/soil", response_class=HTMLResponse)
async def soil_map():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content, status_code=200)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)