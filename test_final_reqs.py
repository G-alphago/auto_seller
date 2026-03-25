from scraper import extract_product
from converter import convert_to_qoo10_row

def test_musinsa_beauty_and_weight():
    # 1. 무신사 뷰티 상품 (카테고리, 브랜드, 무게 테스트)
    url = "https://www.musinsa.com/products/5430926"
    print(f"\n[실제 URL 테스트: {url}]")
    
    product = extract_product(url)
    print(f"추출된 원본 제목: {product.get('title')}")
    print(f"추출된 무게(g): {product.get('weight')}")
    
    row = convert_to_qoo10_row(product)
    print(f"  -> 브랜드 코드 (D열): {row['brand_number']}")
    print(f"  -> 정제된 제목 (E열): {row['item_name']}")
    print(f"  -> 카테고리 코드 (C열): {row['category_number']}")
    print(f"  -> 최종 무게 (AJ열): {row['item_weight']} kg")
    
    # 2. 수동 무게 테스트
    print("\n[수동 무게 테스트]")
    test_data = {"title": "가상 상품", "weight": 700, "main_image": "http://test.com/img.jpg", "options": []}
    row_manual = convert_to_qoo10_row(test_data)
    print(f"원본 700g -> 반영된 무게: {row_manual['item_weight']} kg (기대값: 1.2)")

if __name__ == "__main__":
    test_musinsa_beauty_and_weight()
