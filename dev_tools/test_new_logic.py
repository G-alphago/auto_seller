
import json
import os
from scraper import extract_product
from converter import convert_to_qoo10_row

def test_pdp2_and_brand_rules():
    urls = [
        "https://www.musinsa.com/products/3358359", # Converse (CONVERSE) - PDP1
        "https://www.musinsa.com/products/3773183", # SPAO (SPAO) - PDP1
        "https://www.musinsa.com/products/5902442"  # F2F(에프투에프) - PDP2
    ]
    
    print("상품명 및 브랜드 규칙 통합 테스트 시작...")
    for url in urls:
        print(f"\n[테스트 대상] {url}")
        try:
            result = extract_product(url)
            print(f"추집된 원본 상품명 (Title): {result.get('title')}")
            print(f"추집된 원본 브랜드 (Scraped Brand): {result.get('scraped_brand')}")
            
            qoo10_row = convert_to_qoo10_row(result)
            brand_code = qoo10_row.get('brand_number')
            item_name = qoo10_row.get('item_name')
            
            print(f"변환된 브랜드 코드: {brand_code}")
            print(f"변환된 상품명(일어): {item_name}")
            
            # 검증 로직
            if "5902442" in url:
                if result.get('title') and "티셔츠" in result.get('title'):
                    print("✅ PDP2 상품명 추출 성공!")
                else:
                    print("❌ PDP2 상품명 추출 실패 (비어있거나 잘못됨)")
                
                if result.get('scraped_brand') == "F2F":
                    print("✅ F2F 브랜드 영문 추출 성공!")
                else:
                    print(f"❌ F2F 브랜드 추출 결과: {result.get('scraped_brand')} (F2F 기대됨)")

        except Exception as e:
            print(f"오류 발생: {e}")

if __name__ == "__main__":
    test_pdp2_and_brand_rules()
