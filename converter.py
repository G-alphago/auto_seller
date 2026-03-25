import re
import os
import uuid
import requests
from io import BytesIO
from deep_translator import GoogleTranslator
from PIL import Image
from bs4 import BeautifulSoup
from classifier import match_category
from brand_classifier import extract_brand_info


def get_usd_jpy_rate() -> float:
    """실시간 원→엔 환율 조회"""
    try:
        resp = requests.get(
            "https://api.exchangerate-api.com/v4/latest/KRW",
            timeout=5
        )
        data = resp.json()
        return data["rates"]["JPY"]
    except Exception:
        print("[환율] 실시간 조회 실패 → 기본값 0.106 사용")
        return 0.106


def calculate_price_jpy(price_krw: float) -> int:
    """
    원화 → 엔화 판매가 계산
    공식: (원가÷환율 + 배송비1400) ÷ (1 - 수수료12% - 마진20%)
    """
    rate      = get_usd_jpy_rate()
    shipping  = 1400   # 스마트쉽 배송비 (엔)
    deduction = 0.68   # 1 - 0.12(수수료) - 0.20(마진)

    price_jpy = (price_krw * rate + shipping) / deduction
    return int((price_jpy + 9) // 10 * 10)


def translate_ko_to_ja(text: str) -> str:
    """한국어를 일본어로 자동 번역 (Deep Translator 사용)"""
    if not text or not text.strip():
        return ""
    try:
        # Google 번역기를 무료로 우회하여 사용
        translator = GoogleTranslator(source='ko', target='ja')
        return translator.translate(text)
    except Exception as e:
        print(f"[번역 오류] 원본 텍스트 유지: {e}")
        return text


def translate_html_content(html_str: str) -> str:
    """
    HTML 구조는 유지한 채 사이사이의 한글 텍스트만 추출하여 일본어로 번역 후 다시 조립
    """
    if not html_str or len(html_str) < 10:
        return html_str
        
    try:
        soup = BeautifulSoup(html_str, "html.parser")
        
        # 텍스트 노드만 찾아 번역 (내비게이션 문자열)
        for text_node in soup.find_all(string=True):
            if text_node.parent.name in ['script', 'style']:
                continue
                
            original_text = text_node.string.strip()
            if original_text and any(ord('가') <= ord(c) <= ord('힣') for c in original_text):
                translated_text = translate_ko_to_ja(original_text)
                text_node.replace_with(translated_text)
                
        return str(soup)
    except Exception as e:
        print(f"[HTML 번역 오류] 원본 유지: {e}")
        return html_str


def make_image_square(image_url: str) -> str:
    """
    이미지를 큐텐 가이드에 맞춰 정사각형(흰색 배경 패딩)으로 변환 후 로컬 저장
    """
    if not image_url or not image_url.startswith("http"):
        return image_url
    
    try:
        resp = requests.get(image_url, timeout=10)
        resp.raise_for_status()
        
        img = Image.open(BytesIO(resp.content)).convert("RGB")
        width, height = img.size
        
        # 이미 정사각형이면 원본 URL을 그대로 사용 (업로드 편의성)
        if width == height:
            return image_url
            
        print(f"[이미지 처리] {width}x{height} 비율을 정사각형으로 변환 중...")
        
        # 가장 긴 변을 기준으로 정사각형 캔버스 생성 (배경색: 흰색)
        new_size = max(width, height)
        square_img = Image.new("RGB", (new_size, new_size), (255, 255, 255))
        
        # 원본 이미지를 중앙에 배치
        left = (new_size - width) // 2
        top = (new_size - height) // 2
        square_img.paste(img, (left, top))
        
        # 큐텐 권장 사이즈(최소 600x600 이상)로 리사이징
        if new_size > 800:
            square_img = square_img.resize((800, 800), Image.Resampling.LANCZOS)
        
        # 로컬 폴더에 저장 (outputs/images 폴더 생성)
        save_dir = os.path.join(os.getcwd(), "outputs", "images")
        os.makedirs(save_dir, exist_ok=True)
        
        # 고유한 파일명 생성
        filename = f"main_{uuid.uuid4().hex[:8]}.jpg"
        filepath = os.path.join(save_dir, filename)
        
        square_img.save(filepath, "JPEG", quality=95)
        print(f"  -> 변환 완료: {filepath}")
        
        # 엑셀에는 변환된 로컬 파일의 경로를 반환
        return filepath
        
    except Exception as e:
        print(f"[이미지 처리 오류] 원본 이미지 URL 유지: {e}")
        return image_url


def format_options_qoo10(options: list) -> str:
    """
    Qoo10 옵션 형식 (번역 추가 적용):
    옵션명||*옵션값||*옵션가격||*재고수량||*판매자옵션코드$$
    """
    if not options:
        return ""

    parts = []
    for opt in options[:2]:  # 최대 2단계
        name_ko = opt.get("name", "").strip()
        name_ja = translate_ko_to_ja(name_ko)  # 옵션명 번역
        
        values = opt.get("values", [])[:20]  # 최대 20개
        values = [v.strip() for v in values if v.strip()]
        
        if not name_ko or not values:
            continue
            
        for val_ko in values:
            val_ja = translate_ko_to_ja(val_ko) # 옵션값 번역
            # 옵션명||*옵션값||*추가가격(0)||*재고수량(100)||*판매자코드(빈값)$$
            parts.append(f"{name_ja}||*{val_ja}||*0||*100||*")

    return "$$".join(parts) + "$$" if parts else ""


def clean_item_name(title: str) -> str:
    """Qoo10 상품명 정제 (한국어 상태에서 불필요한 단어 제거)"""
    site_patterns = [
        r'\s*[-|]\s*(사이즈\s*[&＆]\s*후기\s*)?무신사.*$',
        r'\s*[-|]\s*올리브영.*$',
        r'\s*[-|]\s*G마켓.*$',
        r'\s*[-|]\s*11번가.*$',
        r'\s*[-|]\s*옥션.*$',
        r'\|\s*올리브영.*$',
        r'\s*-\s*사이즈\s*[&＆]\s*후기.*$',
        r'\s*\|\s*.*$',  
    ]
    for pat in site_patterns:
        title = re.sub(pat, '', title, flags=re.IGNORECASE)

    title = re.sub(r'[【】★☆♥♡◆◇■□▲△▶▷●○◎※†‡]', '', title)
    title = re.sub(r'[^\w\s\-\.,/&()\[\]%+]', '', title, flags=re.UNICODE)
    title = re.sub(r'\s+', ' ', title).strip()
    return title[:100]


def convert_to_qoo10_row(product: dict) -> dict:
    """크롤링 결과 → Qoo10 엑셀 업로드 형식 변환"""
    
    # 1. 가격 처리
    price_raw = product.get("price", "")
    price_numbers = re.sub(r'[^\d.]', '', str(price_raw))
    try:
        price_krw = float(price_numbers) if price_numbers else 0
    except ValueError:
        price_krw = 0

    price_jpy = calculate_price_jpy(price_krw) if price_krw > 0 else ""

    # 2. 브랜드 추출 및 상품명 정제
    raw_title = product.get("title", "")
    brand_code, cleaned_title_ko = extract_brand_info(raw_title)
    
    # 3. 사이트별 특수문자 및 불필요 키워드 추가 정제
    title_ko = clean_item_name(cleaned_title_ko)
    print(f"[번역] 상품명 번역 중... ({title_ko[:20]}...)")
    title_ja = translate_ko_to_ja(title_ko)

    # 4. 메인 이미지 큐텐 규격화 (정사각형 패딩)
    main_image_url = product.get("main_image", "")
    processed_image_path = make_image_square(main_image_url)

    # 5. 옵션 변환 및 번역
    print("[번역] 옵션 번역 중...")
    option_str = format_options_qoo10(product.get("options", []))

    # 6. 카테고리 매칭 (원본 제목 기준이 더 정확할 수 있음)
    category_id = match_category(raw_title)

    return {
        "item_name":            title_ja,  # 번역된 상품명 적용
        "item_promotion_name":  "",
        "item_status_Y/N/D":    "Y",
        "price_yen":            price_jpy,
        "retail_price_yen":     "",
        "taxrate":              10,
        "quantity":             100,
        "option_info":          option_str, # 번역된 옵션 적용

        "image_main_url":       main_image_url, # HTTP URL 형태 유지
        "image_other_url":      "",

        "item_description":     translate_html_content(product.get("detail_html", "")),
        "start_date":           "",
        "end_date":             "",
        "available_shipping_date": 3,
        "Shipping_number":      "665405", # 고정 배송비 코드
        "item_condition_type":  "1",
        "origin_type":          "2",
        "search_keyword":       "",

        "seller_unique_item_id": "",
        "category_number":      category_id,
        "brand_number":         brand_code,
        "additional_option_info": "",
        "additional_option_text": "",
        "video_url":            "",
        "image_option_info":    "",
        "image_additional_option_info": "",
        "header_html":          "",
        "footer_html":          "",
        "option_number":        "",
        "desired_shipping_date": "",
        "origin_region_id":     "",
        "origin_country_id":    "KR",
        "origin_others":        "",
        "medication_type":      "",
        "item_weight":          "",
        "item_material":        "",
        "model_name":           "",
        "external_product_type": "",
        "external_product_id":  "",
        "manufacture_date":     "",
        "expiration_date_type": "",
        "expiration_date_MFD":  "",
        "expiration_date_PAO":  "",
        "expiration_date_EXP":  "",
        "under18s_display_Y/N": "N",
        "A/S_info":             "",
        "buy_limit_type":       "",
        "buy_limit_date":       "",
        "buy_limit_qty":        "",
    }