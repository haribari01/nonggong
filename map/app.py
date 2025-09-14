from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd
import uvicorn
from typing import Optional

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def home():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content, status_code=200)


@app.get("/api/csv-list")
async def get_csv_list():
    csv_files = [
        {"filename": "SoilFitStat_apple.csv", "display_name": "작물별 토양적성 통계정보"}
    ]
    return JSONResponse(content=csv_files)


@app.get("/api/crops")
async def get_crops(filename: str):
    try:
        df = pd.read_csv(f"data/{filename}")
        crops = df[['soil_Crop_Cd', 'soil_Crop_Nm']].drop_duplicates().sort_values('soil_Crop_Nm')
        return JSONResponse(content=crops.to_dict('records'))
    except Exception as e:
        return JSONResponse(content=[], status_code=500)


@app.get("/api/data")
async def get_map_data(filename: str, crop_code: str):
    try:
        df = pd.read_csv(f"data/{filename}")

        # 선택된 작물 필터링
        df_filtered = df[df['soil_Crop_Cd'] == crop_code]

        # 시도 레벨 데이터만 (3~10자리가 모두 0)
        sido_mask = df_filtered['stdg_Cd'].astype(str).str[2:10] == '00000000'
        sido_data = df_filtered[sido_mask].copy()

        # CTPRVN_CD 생성 (앞 2자리)
        sido_data['ctprvn_cd'] = sido_data['stdg_Cd'].astype(str).str[:2]

        columns = ['ctprvn_cd', 'bjd_Nm', 'soil_Crop_Nm', 'high_Suit_Area', 'suit_Area', 'poss_Area', 'low_Suit_Area',
                   'etc_Area']
        result = sido_data[columns].to_dict('records')

        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content=[], status_code=500)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)