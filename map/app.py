from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd
import uvicorn
from typing import Optional
import os
from data.column_mapping import COLUMN_MAPPING

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
        {"filename": "SoilFitStat_apple.csv", "display_name": "작물별 토양적성 통계정보", "type": "crop"},
        {"filename": "SoilExamStat_pH.csv", "display_name": "농경지화학성 pH 통계정보", "type": "soil"},
        {"filename": "SoilExamStat_Om.csv", "display_name": "농경지화학성 유기물 통계정보", "type": "soil"},
        {"filename": "SoilExamStat_Ap.csv", "display_name": "농경지화학성 유효인산 통계정보", "type": "soil"},
        {"filename": "SoilExamStat_Ka.csv", "display_name": "농경지화학성 칼륨 통계정보", "type": "soil"},
        {"filename": "SoilExamStat_Ca.csv", "display_name": "농경지화학성 칼슘 통계정보", "type": "soil"},
        {"filename": "SoilExamStat_Mg.csv", "display_name": "농경지화학성 마그네슘 통계정보", "type": "soil"},
        {"filename": "SoilExamStat_Sa.csv", "display_name": "농경지화학성 유효규산 통계정보", "type": "soil"},
        {"filename": "SoilCharacStat_DistrbTopograpy.csv", "display_name": "토양도 기반 분포지형 통계 정보", "type": "soil"},
        {"filename": "SoilCharacStat_AmnForm.csv", "display_name": "토양도 기반 퇴적양식 통계 정보", "type": "soil"},
        {"filename": "SoilCharacStat_Tree.csv", "display_name": "토양도 기반 토양목 통계 정보", "type": "soil"},
        {"filename": "SoilCharacStat_Sbr.csv", "display_name": "토양도 기반 토양아목 통계 정보", "type": "soil"},
        {"filename": "SoilCharacStat_DrngGrad.csv", "display_name": "토양도 기반 배수등급 통계 정보", "type": "soil"},
        {"filename": "SoilCharacStat_WashGrad.csv", "display_name": "토양도 기반 침식등급 통계 정보", "type": "soil"},
        {"filename": "SoilCharacStat_TopslGrv.csv", "display_name": "토양도 기반 표토자갈함량 통계 정보", "type": "soil"},
        {"filename": "SoilCharacStat_MainLand.csv", "display_name": "토양도 기반 주토지이용 통계 정보", "type": "soil"},
        {"filename": "SoilCharacStat_FieldGrad.csv", "display_name": "토양도 기반 밭 적성등급 통계 정보", "type": "soil"},
        {"filename": "SoilCharacStat_PaddyObstrcFctr.csv", "display_name": "토양도 기반 논 저해요인 통계 정보", "type": "soil"}
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


@app.get("/api/soil-columns")
async def get_soil_columns(filename: str):
    """토양 성분 CSV의 컬럼 목록을 반환"""
    try:
        df = pd.read_csv(f"data/{filename}")
        # 첫 번째 행(stdg_Cd)과 두 번째 행(bjd_Nm)을 제외한 컬럼들
        columns = df.columns[2:].tolist()

        # column_mapping을 사용해서 한글명으로 변환
        column_info = []
        for col in columns:
            korean_name = COLUMN_MAPPING.get(col, col)
            column_info.append({
                'column': col,
                'display_name': korean_name
            })

        return JSONResponse(content=column_info)
    except Exception as e:
        return JSONResponse(content=[], status_code=500)


@app.get("/api/data")
async def get_map_data(filename: str, crop_code: str = None, level: str = "sido"):
    try:
        df = pd.read_csv(f"data/{filename}")

        # 작물별 데이터와 토양 성분 데이터 구분
        if crop_code:
            # 작물별 데이터 (기존 로직)
            df_filtered = df[df['soil_Crop_Cd'] == crop_code]
        else:
            # 토양 성분 데이터 (새로운 로직)
            df_filtered = df.copy()

        if level == "sido":
            # 시도 레벨 데이터만 (3~10자리가 모두 0)
            sido_mask = df_filtered['stdg_Cd'].astype(str).str[2:10] == '00000000'
            result_data = df_filtered[sido_mask].copy()
            result_data['region_cd'] = result_data['stdg_Cd'].astype(str).str[:2]

        elif level == "sigungu":
            # 시군구 레벨 데이터만 (6~10자리가 모두 0)
            sigungu_mask = df_filtered['stdg_Cd'].astype(str).str[5:10] == '00000'
            result_data = df_filtered[sigungu_mask].copy()
            result_data['region_cd'] = result_data['stdg_Cd'].astype(str).str[:5]

        elif level == "eupmyeondong":
            # 읍면동 레벨 데이터만 (9~10자리가 모두 0)
            emd_mask = df_filtered['stdg_Cd'].astype(str).str[8:10] == '00'
            result_data = df_filtered[emd_mask].copy()
            result_data['region_cd'] = result_data['stdg_Cd'].astype(str).str[:8]

        elif level == "li":
            # 리 레벨 데이터 (10자리 전체)
            result_data = df_filtered.copy()
            result_data['region_cd'] = result_data['stdg_Cd'].astype(str)

        else:
            return JSONResponse(content=[])

        # 작물별 데이터와 토양 성분 데이터에 따라 컬럼 선택
        if crop_code:
            # 작물별 데이터 컬럼
            columns = ['region_cd', 'bjd_Nm', 'soil_Crop_Nm', 'high_Suit_Area', 'suit_Area', 'poss_Area',
                       'low_Suit_Area', 'etc_Area']
        else:
            # 토양 성분 데이터 컬럼 (stdg_Cd, bjd_Nm 제외한 모든 컬럼)
            data_columns = [col for col in result_data.columns if col not in ['stdg_Cd', 'bjd_Nm']]
            columns = ['region_cd', 'bjd_Nm'] + [col for col in data_columns if col != 'region_cd']

        result = result_data[columns].fillna(0).to_dict('records')
        return JSONResponse(content=result)
    except Exception as e:
        print(f"Error: {e}")
        return JSONResponse(content=[], status_code=500)


# CSV 다운로드 API
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