import os
import time
from datetime import datetime
from scraper import extract_product
from converter import convert_to_qoo10_row
from exporter import save_to_excel, save_summary_excel

def run_batch_pipeline(urls: list):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 다중 URL 처리 시작 (총 {len(urls)}개)")
    
    upload_rows = []
    
    output_dir = os.path.join(os.getcwd(), "outputs")
    os.makedirs(output_dir, exist_ok=True)
    
    for i, url in enumerate(urls, 1):
        print(f"\n--- [{i}/{len(urls)}] 처리 중: {url} ---")
        try:
            # 1. 스크래핑
            product_data = extract_product(url)
            
            # 2. 변환 및 번역
            row = convert_to_qoo10_row(product_data)
            
            # 3. 추가 정보 기록 (요약용)
            row["source_url"] = url
            
            upload_rows.append(row)
            print(f"  -> 완료: {row.get('item_name', 'Unknown')[:30]}...")
            
        except Exception as e:
            print(f"  -> [오류 발생] {url}: {e}")
            continue
            
        # 사이트 부하 방지 및 안정성을 위한 대기 (필요시)
        if i < len(urls):
            time.sleep(1)

    if not upload_rows:
        print("\n[실패] 처리된 상품이 없습니다.")
        return

    # 4. 엑셀 파일 생성
    print("\n--- 엑셀 파일 생성 중 ---")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    upload_file = f"qoo10_upload_{timestamp}.xlsx"
    summary_file = f"summary_{timestamp}.xlsx"
    
    upload_path = save_to_excel(upload_rows, output_dir=output_dir, filename=upload_file)
    summary_path = save_summary_excel(upload_rows, output_dir=output_dir, filename=summary_file)
    
    print(f"OK: 큐텐 업로드 파일 생성 완료 -> {upload_path}")
    print(f"OK: 상품 관리 요약 파일 생성 완료 -> {summary_path}")
    print("\n[최종 작업 완료]")

if __name__ == "__main__":
    # 테스트용 URL 리스트 (무신사, 11번가, 네이버 스마트스토어 등)
    # 실제 테스트 시 유효한 URL로 교체 가능
    test_urls = [
        "https://www.musinsa.com/products/4397792", # 무신사 샘플 1
        "https://www.musinsa.com/products/4523674", # 무신사 샘플 2
    ]
    
    # 실제 동작 확인을 위해 유효한 URL로 테스트하는 것이 좋습니다.
    # 사용자가 제시한 자율 테스트를 위해 2~3개 URL로 실행
    run_batch_pipeline(test_urls)
