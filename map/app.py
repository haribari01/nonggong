from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd
import json
import uvicorn

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
@app.get("/api/soil", response_class=HTMLResponse)
async def soil_map():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content, status_code=200)


@app.get("/api/soil-data")
async def get_soil_data():
    df = pd.read_csv("data/SoilFitStat_apple.csv")
    sido_data = df[df['stdg_Cd'].astype(str).str[2:10] == '00000000'].copy()
    sido_data['ctprvn_cd'] = sido_data['stdg_Cd'].astype(str).str[:2]

    result = sido_data[
        ['ctprvn_cd', 'bjd_Nm', 'high_Suit_Area', 'suit_Area', 'poss_Area', 'low_Suit_Area', 'etc_Area']].to_dict(
        'records')
    return JSONResponse(content=result)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)