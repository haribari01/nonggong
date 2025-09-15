import os
import csv
import requests
import xml.etree.ElementTree as ET
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from urllib.parse import quote


class SoilAPICollector:
    def __init__(self):
        # 인증키
        self.SERVICE_KEY = "fOnrt/nVSCnLI05XSbmySE3F11nxviUIhefxXDnVGGbJusKK04jb0OIAkpbgUuRyca9HwxTfHbi1GiN4UyL/DQ=="

        # API 설정 - [그룹, 순번, API명, URL, 파일명]
        self.api_configs = [
            # 1번 그룹: 농경지화학성 통계정보
            [1, 1, "농경지화학성_유기물", "http://apis.data.go.kr/1390802/SoilEnviron/SoilExamStat/V2/getFarmExamOmInfo", "1-1"],
            [1, 2, "농경지화학성_유효인산", "http://apis.data.go.kr/1390802/SoilEnviron/SoilExamStat/V2/getFarmExamApInfo",
             "1-2"],
            [1, 3, "농경지화학성_칼륨", "http://apis.data.go.kr/1390802/SoilEnviron/SoilExamStat/V2/getFarmExamKalInfo", "1-3"],
            [1, 4, "농경지화학성_pH", "http://apis.data.go.kr/1390802/SoilEnviron/SoilExamStat/V2/getFarmExamPhInfo", "1-4"],
            [1, 5, "농경지화학성_마그네슘", "http://apis.data.go.kr/1390802/SoilEnviron/SoilExamStat/V2/getFarmExamMgInfo",
             "1-5"],
            [1, 6, "농경지화학성_유효규산", "http://apis.data.go.kr/1390802/SoilEnviron/SoilExamStat/V2/getFarmExamSaInfo",
             "1-6"],
            [1, 7, "농경지화학성_칼슘", "http://apis.data.go.kr/1390802/SoilEnviron/SoilExamStat/V2/getFarmExamCalInfo", "1-7"],

            # 2번 그룹: 토양특성 통계정보
            [2, 1, "토양특성_배수등급",
             "http://apis.data.go.kr/1390802/SoilEnviron/SoilCharacStat/V2/getSoilDrngGradSpecificInfo", "2-1"],
            [2, 2, "토양특성_침식등급",
             "http://apis.data.go.kr/1390802/SoilEnviron/SoilCharacStat/V2/getSoilWashGradSpecificInfo", "2-2"],
            [2, 3, "토양특성_표토자갈함량",
             "http://apis.data.go.kr/1390802/SoilEnviron/SoilCharacStat/V2/getSoilTopslGrvSpecificInfo", "2-3"],
            [2, 4, "토양특성_분포지형",
             "http://apis.data.go.kr/1390802/SoilEnviron/SoilCharacStat/V2/getSoilDistrbTopogrpySpecificInfo", "2-4"],
            [2, 5, "토양특성_퇴적양식",
             "http://apis.data.go.kr/1390802/SoilEnviron/SoilCharacStat/V2/getSoilAmnFormSpecificInfo", "2-5"],
            [2, 6, "토양특성_토양목", "http://apis.data.go.kr/1390802/SoilEnviron/SoilCharacStat/V2/getSoilTreeSpecificInfo",
             "2-6"],
            [2, 7, "토양특성_토양아목", "http://apis.data.go.kr/1390802/SoilEnviron/SoilCharacStat/V2/getSoilSbrSpecificInfo",
             "2-7"],
            [2, 8, "토양특성_주토지이용",
             "http://apis.data.go.kr/1390802/SoilEnviron/SoilCharacStat/V2/getSoilMainLandSpecificInfo", "2-8"],
            [2, 9, "토양특성_논적성등급",
             "http://apis.data.go.kr/1390802/SoilEnviron/SoilCharacStat/V2/getSoilPaddyGradSpecificInfo", "2-9"],
            [2, 10, "토양특성_밭적성등급",
             "http://apis.data.go.kr/1390802/SoilEnviron/SoilCharacStat/V2/getSoilFieldGradSpecificInfo", "2-10"]
        ]

        # 스레드 안전을 위한 락
        self.print_lock = Lock()

    def read_pnu_codes(self, filename="sido_pnu.csv"):
        """sido_pnu.csv 파일에서 첫번째 열의 두번째 행부터 법정동코드를 읽어오는 함수"""
        pnu_codes = []
        try:
            # UTF-8로 먼저 시도
            with open(filename, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # 헤더 건너뛰기
                for row in reader:
                    if len(row) > 0 and row[0].strip():  # 첫 번째 열이 비어있지 않은 경우만
                        pnu_codes.append(row[0].strip())  # 첫 번째 열의 법정동코드, 공백 제거
        except UnicodeDecodeError:
            # CP1252로 재시도
            with open(filename, 'r', encoding='cp1252') as f:
                reader = csv.reader(f)
                next(reader)  # 헤더 건너뛰기
                for row in reader:
                    if len(row) > 0 and row[0].strip():
                        pnu_codes.append(row[0].strip())  # 첫 번째 열의 법정동코드, 공백 제거
        except FileNotFoundError:
            print(f"파일 {filename}을 찾을 수 없습니다.")
            return []
        except Exception as e:
            print(f"파일 읽기 오류: {e}")
            return []

        return pnu_codes

    def get_api_data(self, url, stdg_cd):
        """개별 API를 호출하여 데이터를 가져오는 함수"""
        params = {
            'serviceKey': self.SERVICE_KEY,
            'STDG_CD': stdg_cd
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            # XML 파싱
            root = ET.fromstring(response.content)

            # 결과 코드 확인
            result_code = root.find('.//result_Code')
            result_msg = root.find('.//result_Msg')

            if result_code is not None and result_code.text == '200':
                # 성공적으로 데이터를 받은 경우
                item = root.find('.//item')
                if item is not None:
                    data = {}
                    for child in item:
                        data[child.tag] = child.text
                    return data
                else:
                    return None
            else:
                error_msg = result_msg.text if result_msg is not None else "알 수 없는 오류"
                with self.print_lock:
                    print(f"API 오류 - STDG_CD: {stdg_cd}, 오류: {error_msg}")
                return None

        except requests.exceptions.RequestException as e:
            with self.print_lock:
                print(f"요청 오류 - STDG_CD: {stdg_cd}, 오류: {e}")
            return None
        except ET.ParseError as e:
            with self.print_lock:
                print(f"XML 파싱 오류 - STDG_CD: {stdg_cd}, 오류: {e}")
            return None

    def save_to_csv(self, data_list, filename):
        """데이터를 CSV 파일로 저장하는 함수"""
        if not data_list:
            with self.print_lock:
                print(f"{filename}: 저장할 데이터가 없습니다.")
            return

        # 모든 데이터에서 필드명 수집
        all_fieldnames = set()
        for data in data_list:
            all_fieldnames.update(data.keys())

        # 필드명을 리스트로 변환하고 정렬
        fieldnames = sorted(list(all_fieldnames))

        try:
            with open(f"{filename}.csv", 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for data in data_list:
                    # 필드명이 일치하는 데이터만 추출
                    row_data = {field: data.get(field, '') for field in fieldnames}
                    writer.writerow(row_data)

            with self.print_lock:
                print(f"✓ {filename}.csv 저장 완료: {len(data_list)}건")

        except Exception as e:
            with self.print_lock:
                print(f"CSV 저장 오류 - {filename}: {e}")

    def collect_single_api_data(self, api_config, pnu_codes):
        """단일 API의 모든 데이터를 수집하는 함수"""
        group, seq, api_name, url, file_prefix = api_config

        with self.print_lock:
            print(f"\n=== {api_name} 수집 시작 ===")

        collected_data = []
        successful_count = 0

        for i, pnu_code in enumerate(pnu_codes):
            # 10자리 코드로 변환 (필요시)
            stdg_cd = str(pnu_code).zfill(10)

            # 진행률 출력 (매 5건마다)
            if (i + 1) % 5 == 0 or i == 0 or i == len(pnu_codes) - 1:
                with self.print_lock:
                    print(f"{api_name}: {i + 1}/{len(pnu_codes)} 진행 중... ({(i + 1) / len(pnu_codes) * 100:.1f}%)")

            data = self.get_api_data(url, stdg_cd)

            if data:
                collected_data.append(data)
                successful_count += 1

            # 랜덤 대기 시간 (1.0 ~ 1.1초) - 매크로 방지
            wait_time = random.uniform(1.0, 1.1)
            time.sleep(wait_time)

        # 결과 저장
        self.save_to_csv(collected_data, file_prefix)

        with self.print_lock:
            print(f"=== {api_name} 완료: {successful_count}/{len(pnu_codes)}건 수집 ===")

        return {
            'api_name': api_name,
            'total': len(pnu_codes),
            'successful': successful_count,
            'failed': len(pnu_codes) - successful_count
        }

    def collect_all_data_parallel(self, max_workers=5):
        """모든 API 데이터를 병렬로 수집하는 메인 함수"""
        print("sido_pnu.csv에서 법정동코드를 읽어오는 중...")
        pnu_codes = self.read_pnu_codes()

        if not pnu_codes:
            print("법정동코드를 읽어올 수 없습니다. sido_pnu.csv 파일을 확인해주세요.")
            return

        print(f"총 {len(pnu_codes)}개의 법정동코드를 읽어왔습니다.")
        print(f"법정동코드 목록: {pnu_codes}")
        print(f"총 {len(self.api_configs)}개 API를 {max_workers}개 스레드로 병렬 처리합니다.")
        print(f"예상 소요 시간: 약 {len(pnu_codes) * 1.05 / 60:.1f}분")
        print("=" * 60)

        # 결과 저장용
        results = []

        # ThreadPoolExecutor를 사용한 병렬 처리
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 모든 API 작업 제출
            future_to_config = {
                executor.submit(self.collect_single_api_data, config, pnu_codes): config
                for config in self.api_configs
            }

            # 작업 완료를 기다리며 결과 수집
            for future in as_completed(future_to_config):
                config = future_to_config[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as exc:
                    with self.print_lock:
                        print(f"{config[2]} API에서 오류 발생: {exc}")

        # 최종 결과 출력
        print("\n" + "=" * 60)
        print("=== 전체 수집 결과 ===")
        total_successful = 0
        total_requests = 0

        for result in results:
            print(f"{result['api_name']}: {result['successful']}/{result['total']}건 성공")
            total_successful += result['successful']
            total_requests += result['total']

        print(f"\n전체 통계: {total_successful}/{total_requests}건 성공 "
              f"(성공률: {total_successful / total_requests * 100:.1f}%)")
        print("모든 데이터 수집이 완료되었습니다!")

        # 생성된 파일 목록 출력
        print("\n=== 생성된 CSV 파일 목록 ===")
        for config in self.api_configs:
            file_name = f"{config[4]}.csv"
            if os.path.exists(file_name):
                print(f"✓ {file_name}")
            else:
                print(f"✗ {file_name} (생성되지 않음)")


def main():
    collector = SoilAPICollector()

    # 병렬 처리 실행 (서버 부하를 줄이기 위해 2개 스레드로 감소)
    # 타임아웃이 계속 발생하면 max_workers=1로 순차처리도 고려해보세요
    collector.collect_all_data_parallel(max_workers=2)


if __name__ == "__main__":
    main()