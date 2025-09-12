from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List
import os
import glob
import pandas as pd

app = FastAPI(title="Soil Suitability Map")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

BASE_DIR = os.path.abspath(os.getcwd())
STATIC_DIR = os.path.join(BASE_DIR, "static")
DATA_DIR = os.path.join(BASE_DIR, "data")


def _safe_join(base: str, path: str) -> str:
    """안전한 경로 결합"""
    target = os.path.abspath(os.path.join(base, path))
    if not target.startswith(base):
        raise HTTPException(status_code=400, detail="Invalid path")
    return target


@app.get("/", response_class=FileResponse)
def index():
    """메인 페이지 반환"""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_path, media_type="text/html")


@app.get("/list_csv", response_class=JSONResponse)
def list_csv(
        dir: str = Query("data", description="검색할 디렉토리"),
        pattern: str = Query("*.csv", description="glob 패턴")
) -> List[str]:
    """CSV 파일 목록 반환"""
    root = _safe_join(BASE_DIR, dir)
    if not os.path.isdir(root):
        raise HTTPException(status_code=400, detail="Directory not found")

    glob_pattern = os.path.join(root, pattern)
    files = sorted(glob.glob(glob_pattern))

    # 상대 경로로 변환
    return [os.path.relpath(p, BASE_DIR).replace("\\", "/") for p in files]


@app.get("/api/crops")
def get_crops():
    """작물 목록 반환"""
    try:
        csv_path = os.path.join(DATA_DIR, "soil_suitability_sgg.csv")
        df = pd.read_csv(csv_path, encoding='utf-8')

        # 작물 목록 추출 (중복 제거)
        crops = df[['soil_Crop_Cd', 'soil_Crop_Nm']].drop_duplicates()
        crops_list = []

        for _, row in crops.iterrows():
            crops_list.append({
                'code': row['soil_Crop_Cd'],
                'name': row['soil_Crop_Nm']
            })

        return sorted(crops_list, key=lambda x: x['name'])

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading crops: {str(e)}")


@app.get("/api/suitability")
def get_suitability_data(crop_code: str = Query(..., description="작물 코드")):
    """특정 작물의 토양 적합성 데이터 반환"""
    try:
        csv_path = os.path.join(DATA_DIR, "soil_suitability_sgg.csv")
        df = pd.read_csv(csv_path, encoding='utf-8')

        # 특정 작물 필터링
        crop_data = df[df['soil_Crop_Cd'] == crop_code]

        if crop_data.empty:
            raise HTTPException(status_code=404, detail="Crop not found")

        # 데이터 변환
        result = []
        for _, row in crop_data.iterrows():
            # 표준화 코드를 지역명으로 매핑하기 위해 앞 5자리만 사용 (시군구 레벨)
            region_code = str(row['stdg_Cd'])[:5] + "00000"

            # 총 면적 계산
            total_area = (row['high_Suit_Area'] + row['suit_Area'] +
                          row['poss_Area'] + row['low_Suit_Area'] + row['etc_Area'])

            # 적합성 점수 계산 (높을수록 적합)
            if total_area > 0:
                suitability_score = (
                                            row['high_Suit_Area'] * 4 +
                                            row['suit_Area'] * 3 +
                                            row['poss_Area'] * 2 +
                                            row['low_Suit_Area'] * 1 +
                                            row['etc_Area'] * 0
                                    ) / total_area
            else:
                suitability_score = 0

            result.append({
                'region_code': region_code,
                'region_name': row['bjd_Nm'],
                'high_suit_area': int(row['high_Suit_Area']),
                'suit_area': int(row['suit_Area']),
                'poss_area': int(row['poss_Area']),
                'low_suit_area': int(row['low_Suit_Area']),
                'etc_area': int(row['etc_Area']),
                'total_area': int(total_area),
                'suitability_score': round(suitability_score, 2)
            })

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading data: {str(e)}")


# 정적 파일 서빙
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8080)  # 포트를 8080으로 변경