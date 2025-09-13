import csv
import requests
import time
import random
import xml.etree.ElementTree as ET
from datetime import datetime
import os
import threading
from queue import Queue
import concurrent.futures


def read_pnu_codes(filename="pnu.csv"):
    """PNU CSV 파일에서 행정코드를 읽어오는 함수"""
    pnu_codes = []
    try:
        # UTF-8로 먼저 시도
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # 헤더 건너뛰기
            for row in reader:
                if len(row) > 0:
                    pnu_codes.append(row[0])  # 첫 번째 열의 행정코드
    except UnicodeDecodeError:
        # CP1252로 재시도
        with open(filename, 'r', encoding='cp1252') as f:
            reader = csv.reader(f)
            next(reader)  # 헤더 건너뛰기
            for row in reader:
                if len(row) > 0:
                    pnu_codes.append(row[0])  # 첫 번째 열의 행정코드

    return pnu_codes


def call_soil_api(service_key, stdg_cd, crop_cd):
    """토양적성 API 호출 함수"""
    base_url = "http://apis.data.go.kr/1390802/SoilEnviron/SoilFitStat/V2/getSoilCropFitInfo"

    params = {
        'serviceKey': service_key,
        'STDG_CD': stdg_cd,
        'soil_Crop_CD': crop_cd
    }

    try:
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"API 호출 실패 - STDG_CD: {stdg_cd}, crop_CD: {crop_cd}, 에러: {e}")
        return None


def parse_xml_response(xml_data):
    """XML 응답을 파싱하여 딕셔너리로 변환"""
    try:
        root = ET.fromstring(xml_data)

        # 결과 코드 확인
        result_code = root.find('.//result_Code')
        if result_code is not None and result_code.text != '200':
            result_msg = root.find('.//result_Msg')
            error_msg = result_msg.text if result_msg is not None else "Unknown error"
            print(f"API 에러 - 코드: {result_code.text}, 메시지: {error_msg}")
            return None

        # 데이터 추출
        item = root.find('.//item')
        if item is not None:
            data = {}
            for child in item:
                data[child.tag] = child.text
            return data
        else:
            print("응답에 데이터가 없습니다.")
            return None

    except ET.ParseError as e:
        print(f"XML 파싱 에러: {e}")
        return None


def save_to_csv(data_list, filename):
    """데이터 리스트를 CSV 파일로 저장"""
    if not data_list:
        print(f"저장할 데이터가 없습니다: {filename}")
        return

    # CSV 헤더 정의
    headers = [
        'stdg_Cd', 'bjd_Nm', 'soil_Crop_Cd', 'soil_Crop_Nm',
        'high_Suit_Area', 'suit_Area', 'poss_Area', 'low_Suit_Area', 'etc_Area'
    ]

    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data_list)

    print(f"{filename} 파일이 저장되었습니다. (총 {len(data_list)}개 레코드)")


def worker_thread(service_key, crop_code, pnu_queue, result_list, thread_id, total_count, lock):
    """워커 스레드 함수"""
    processed_count = 0

    while True:
        try:
            pnu_code = pnu_queue.get(timeout=1)
        except:
            break  # 큐가 비어있으면 종료

        try:
            # 랜덤 대기 (1~1.1초)
            sleep_time = 1 + random.uniform(0, 0.1)
            time.sleep(sleep_time)

            # API 호출
            xml_response = call_soil_api(service_key, pnu_code, crop_code)

            if xml_response:
                # XML 파싱
                parsed_data = parse_xml_response(xml_response)
                if parsed_data:
                    with lock:
                        result_list.append(parsed_data)
                        processed_count += 1
                        current_total = len(result_list)
                        print(
                            f"스레드 {thread_id}: {current_total}/{total_count} ({current_total / total_count * 100:.1f}%) - "
                            f"PNU: {pnu_code} → {parsed_data.get('bjd_Nm', 'Unknown')}")
                else:
                    with lock:
                        processed_count += 1
                        current_total = len(result_list)
                        print(f"스레드 {thread_id}: 데이터 없음 - PNU: {pnu_code}")
            else:
                with lock:
                    processed_count += 1
                    print(f"스레드 {thread_id}: API 호출 실패 - PNU: {pnu_code}")

        except Exception as e:
            with lock:
                print(f"스레드 {thread_id} 에러: {e}")

        finally:
            pnu_queue.task_done()


def main():
    # 설정
    SERVICE_KEY = "fOnrt/nVSCnLI05XSbmySE3F11nxviUIhefxXDnVGGbJusKK04jb0OIAkpbgUuRyca9HwxTfHbi1GiN4UyL/DQ=="
    CROP_CODE = 'CR005'  # 사과만
    OUTPUT_FILE = 'apple.csv'
    NUM_THREADS = 2  # 스레드 개수

    # PNU 코드 읽기
    print("PNU 코드를 읽고 있습니다...")
    pnu_codes = read_pnu_codes("pnu.csv")
    print(f"총 {len(pnu_codes)}개의 PNU 코드를 읽었습니다.")

    if not pnu_codes:
        print("PNU 코드를 읽을 수 없습니다. pnu.csv 파일을 확인해주세요.")
        return

    # 큐와 결과 리스트 생성
    pnu_queue = Queue()
    result_list = []
    lock = threading.Lock()

    # 큐에 PNU 코드 추가
    for pnu_code in pnu_codes:
        pnu_queue.put(pnu_code)

    print(f"\n=== 사과 데이터 수집 시작 ({NUM_THREADS}개 스레드) ===")

    # 스레드 생성 및 시작
    threads = []
    for i in range(NUM_THREADS):
        thread = threading.Thread(
            target=worker_thread,
            args=(SERVICE_KEY, CROP_CODE, pnu_queue, result_list, i + 1, len(pnu_codes), lock)
        )
        thread.daemon = True
        thread.start()
        threads.append(thread)
        print(f"스레드 {i + 1} 시작됨")

    # 모든 작업 완료 대기
    pnu_queue.join()

    # 스레드 종료 대기
    for thread in threads:
        thread.join()

    # 결과를 PNU 코드 순서로 정렬 (옵션)
    result_list.sort(key=lambda x: x.get('stdg_Cd', ''))

    # CSV 파일로 저장
    print(f"\n사과 데이터를 {OUTPUT_FILE}에 저장 중...")
    save_to_csv(result_list, OUTPUT_FILE)

    print(f"\n=== 사과 데이터 수집 완료! ===")
    print(f"총 수집된 레코드: {len(result_list)}개")


if __name__ == "__main__":
    # 시작 시간 기록
    start_time = datetime.now()
    print(f"데이터 수집을 시작합니다. 시작 시간: {start_time}")

    main()

    # 종료 시간 기록
    end_time = datetime.now()
    duration = end_time - start_time
    print(f"데이터 수집이 완료되었습니다. 종료 시간: {end_time}")
    print(f"총 소요 시간: {duration}")