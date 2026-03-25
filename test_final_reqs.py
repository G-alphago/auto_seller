from converter import convert_to_qoo10_row

def test_new_requirements():
    test_cases = [
        {
            "title": "정말알수없는상품", # 카테고리 매칭이 어려울 법한 제목
            "price": "50000",
            "main_image": "http://image.server.com/test.jpg",
            "options": []
        },
        {
            "title": "여성용 정장 바지",
            "price": "30000",
            "main_image": "https://shopping-phinf.pstatic.net/main_123/123.jpg",
            "options": []
        }
    ]
    
    print(f"\n[신규 요구사항 통합 테스트]")
    for product in test_cases:
        row = convert_to_qoo10_row(product)
        print(f"제목: {product['title']}")
        print(f"  -> 카테고리 코드(C열): {row['category_number']}")
        print(f"  -> 대표 이미지(R열): {row['image_main_url']}")
        print(f"  -> 배송비 번호(Y열): {row['Shipping_number']}")
        print("-" * 50)

if __name__ == "__main__":
    test_new_requirements()
