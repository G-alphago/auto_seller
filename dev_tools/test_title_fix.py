from scraper import extract_product
from converter import convert_to_qoo10_row

def test_musinsa_title_fix():
    url = "https://www.musinsa.com/products/5430926"
    print(f"\n[무신사 제목 추출 테스트: {url}]")
    
    product = extract_product(url)
    print(f"1. 추출된 원본 제목 (KOR): {product.get('title')}")
    
    row = convert_to_qoo10_row(product)
    print(f"2. 번역 및 정제된 제목 (JPN): {row['item_name']}")
    
    # 검증 포인트
    title_kor = product.get('title', '')
    if "[2개부터 구매가능]" in title_kor and "후기" not in title_kor and "리뷰" not in title_kor:
        print("\n✅ 성공: 접두어가 포함되었고 불필요한 접미사가 제거되었습니다.")
    else:
        print("\n❌ 실패: 제목 추출 로직 확인 필요")

if __name__ == "__main__":
    test_musinsa_title_fix()
