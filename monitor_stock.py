import os
import glob
import time
import openpyxl
from scraper import extract_product, extract_with_playwright
from converter import calculate_price_jpy
import re

def extract_numbers(price_str):
    """가격 문자열에서 숫자 부분만 추출 (예: '10,000원' -> 10000)"""
    if not price_str: return 0
    # 문자열에서 숫자만 찾아 합침
    nums = re.findall(r'\d+', str(price_str))
    if not nums: return 0
    return int(''.join(nums))

def monitor_stock():
    outputs_dir = os.path.join(os.path.dirname(__file__), "outputs")
    file_pattern = os.path.join(outputs_dir, "*summary_*.xlsx")
    summary_files = glob.glob(file_pattern)

    if not summary_files:
        print("모니터링 대상 파일(summary_*.xlsx)을 찾을 수 없습니다.")
        return

    print(f"총 {len(summary_files)}개의 파일을 모니터링합니다.")

    for file_path in summary_files:
        print(f"\n[작업 시작] 파일: {os.path.basename(file_path)}")
        try:
            wb = openpyxl.load_workbook(file_path)
            ws = wb.active

            # 첫 행은 헤더이므로 E1에 '비고' 헤더 추가
            if ws.cell(row=1, column=5).value != "비고":
                ws.cell(row=1, column=5).value = "비고"

            # 데이터 행 (2번째 행부터)
            for row in range(2, ws.max_row + 1):
                url = ws.cell(row=row, column=2).value
                old_price_str = ws.cell(row=row, column=3).value
                old_options_str = ws.cell(row=row, column=4).value

                if not url or "http" not in str(url):
                    continue

                print(f"[{row-1}/{ws.max_row-1}] {url} 스크래핑 시도...")
                try:
                    product_data = extract_product(url)
                    
                    # 데이터 부족 시 Playwright 재시도 (scraper 내부적으로 하지만 1차 실패 시)
                    if not product_data.get("price") and not product_data.get("title"):
                        print(f"  -> requests 실패, Playwright 재시도...")
                        product_data = extract_with_playwright(url)

                    time.sleep(2)  # 차단 방지

                    new_price_str = product_data.get("price", "")
                    new_options = product_data.get("options", [])
                    
                    old_price_num = extract_numbers(old_price_str)
                    new_price_krw = extract_numbers(new_price_str)
                    new_price_num = calculate_price_jpy(new_price_krw) if new_price_krw > 0 else 0

                    remark = ""
                    options_str = ""

                    # 1. 품절 판단
                    # 아예 가격/제목이 없으면 상품 페이지가 내려간 것
                    if not new_price_str and not product_data.get("title"):
                        remark = "품절"
                    else:
                        # 2. 가격 비교
                        if old_price_num > 0 and new_price_num > 0 and old_price_num != new_price_num:
                            remark = f"가격 변동: {old_price_num}엔 -> {new_price_num}엔"
                        
                        # 일부 옵션 품절 판단
                        if old_options_str and len(new_options) == 0 and "옵션" in str(old_options_str):
                            pass
                        
                    if not remark and new_price_num == 0:
                        remark = "판매 중지 또는 가격 정보 없음(품절 의심)"

                    # 변동 사항이 없으면 '정상'으로 기록
                    if not remark:
                        remark = "정상"

                    ws.cell(row=row, column=5).value = remark
                    
                    if remark != "정상":
                        print(f"  -> [업데이트] {remark}")
                    else:
                        print(f"  -> 정상 (변동 없음)")

                except Exception as e:
                    print(f"  -> 오류 발생: {e}")
                    ws.cell(row=row, column=5).value = f"스크래핑 에러: {e}"

            wb.save(file_path)
            print(f"[저장 완료] 파일: {os.path.basename(file_path)}")

        except Exception as e:
            print(f"[엑셀 오류] {file_path} 처리 중 문제 발생: {e}")

    print("\n[모든 모니터링 작업 완료]")

if __name__ == "__main__":
    monitor_stock()
