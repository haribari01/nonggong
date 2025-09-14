from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd
import uvicorn
from typing import Optional
import os

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
async def get_map_data(filename: str, crop_code: str, level: str = "sido"):
    try:
        df = pd.read_csv(f"data/{filename}")

        # 선택된 작물 필터링
        df_filtered = df[df['soil_Crop_Cd'] == crop_code]

        if level == "sido":
            # 시도 레벨 데이터만 (3~10자리가 모두 0)
            sido_mask = df_filtered['stdg_Cd'].astype(str).str[2:10] == '00000000'
            sido_data = df_filtered[sido_mask].copy()

            # CTPRVN_CD 생성 (앞 2자리)
            sido_data['region_cd'] = sido_data['stdg_Cd'].astype(str).str[:2]

        elif level == "sigungu":
            # 시군구 레벨 데이터만 (6~10자리가 모두 0)
            sigungu_mask = df_filtered['stdg_Cd'].astype(str).str[5:10] == '00000'
            sigungu_data = df_filtered[sigungu_mask].copy()

            # SIG_CD 생성 (앞 5자리)
            sigungu_data['region_cd'] = sigungu_data['stdg_Cd'].astype(str).str[:5]
            result_data = sigungu_data

        elif level == "eupmyeondong":
            # 읍면동 레벨 데이터만 (9~10자리가 모두 0)
            emd_mask = df_filtered['stdg_Cd'].astype(str).str[8:10] == '00'
            emd_data = df_filtered[emd_mask].copy()

            # EMD_CD 생성 (앞 8자리)
            emd_data['region_cd'] = emd_data['stdg_Cd'].astype(str).str[:8]
            result_data = emd_data

        elif level == "li":
            # 리 레벨 데이터 (10자리 전체)
            li_data = df_filtered.copy()

            # LI_CD 생성 (10자리 전체)
            li_data['region_cd'] = li_data['stdg_Cd'].astype(str)
            result_data = li_data

        else:
            return JSONResponse(content=[])

        # 시도는 이미 설정되어 있으므로 다른 레벨만 처리
        if level != "sido":
            columns = ['region_cd', 'bjd_Nm', 'soil_Crop_Nm', 'high_Suit_Area', 'suit_Area', 'poss_Area',
                       'low_Suit_Area', 'etc_Area']
            result = result_data[columns].to_dict('records')
        else:
            columns = ['region_cd', 'bjd_Nm', 'soil_Crop_Nm', 'high_Suit_Area', 'suit_Area', 'poss_Area',
                       'low_Suit_Area', 'etc_Area']
            result = sido_data[columns].to_dict('records')

        return JSONResponse(content=result)
    except Exception as e:
        print(f"Error: {e}")
        return JSONResponse(content=[], status_code=500)


# CSV 다운로드 API 추가
@app.get("/api/download-csv")
async def download_csv(filename: str):
    try:
        file_path = f"data/{filename}"

        # 파일 존재 확인
        if not os.path.exists(file_path):
            return JSONResponse(content={"error": "File not found"}, status_code=404)

        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='text/csv'
        )
    except Exception as e:
        print(f"Download error: {e}")
        return JSONResponse(content={"error": "Download failed"}, status_code=500)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)