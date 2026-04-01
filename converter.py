import re
import os
import uuid
import requests
from datetime import datetime, timedelta
from io import BytesIO
from deep_translator import GoogleTranslator
from PIL import Image
from bs4 import BeautifulSoup
from classifier import match_category
from brand_classifier import extract_brand_info
from scraper import generate_product_description


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


def extract_only_images_from_html(html_str: str) -> str:
    """
    상세 HTML에서 <img> 태그만 추출하고 스타일 보정 (링크/배너/텍스트 제거용)
    """
    if not html_str:
        return ""
    try:
        soup = BeautifulSoup(html_str, "html.parser")
        images = soup.find_all("img")
        img_tags = []
        for img in images:
            # 큐텐 권장 스타일 적용 (중앙 정렬 및 반응형 너비)
            img['style'] = "max-width: 100%; display: block; margin: 10px auto;"
            # lazy loading 방지를 위해 src 속성 보장 (data-src 등 처리)
            if not img.get('src') and img.get('data-src'):
                img['src'] = img['data-src']
            
            # 불필요한 속성 제거
            for attr in ['onclick', 'border', 'hspace', 'vspace']:
                if img.has_attr(attr):
                    del img[attr]
            
            img_tags.append(str(img))
        return "".join(img_tags)
    except Exception as e:
        print(f"[이미지 추출 오류] {e}")
        return ""


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
        # 1. 원색 변환 및 투명 배경 대응
        if img.mode in ("RGBA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3] if img.mode == "RGBA" else None)
            img = background
        else:
            img = img.convert("RGB")

        width, height = img.size
        print(f"[이미지 처리] {width}x{height} 상품 이미지 정규화 중 (상하좌우 여백 확보)...")
        
        # 2. 800x800 캔버스를 기준으로 작업 (큐텐 권장 최소 사이즈)
        target_size = 800
        # 상품 이미지가 차지할 최대 영역 (약 80% 사용, 상하좌우 10%씩 여백 확보)
        max_inner_size = int(target_size * 0.8)
        
        # 3. 원본 이미지 비율 유지하며 max_inner_size에 맞게 리사이징
        ratio = min(max_inner_size / width, max_inner_size / height)
        new_w = int(width * ratio)
        new_h = int(height * ratio)
        img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # 4. 800x800 흰색 캔버스 생성 및 중앙 배치
        square_img = Image.new("RGB", (target_size, target_size), (255, 255, 255))
        left = (target_size - new_w) // 2
        top = (target_size - new_h) // 2
        square_img.paste(img_resized, (left, top))
        
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
    Qoo10 옵션 형식 (N열):
    1단계: 옵션명1||*옵션값1||*옵션가격||*재고수량||*판매자옵션코드$$
    2단계: 옵션명1||*옵션값1||*옵션명2||*옵션값2||*옵션가격||*재고수량||*판매자옵션코드$$
    """
    if not options:
        return ""

    parts = []
    # Qoo10은 N열 기준 최대 2단계까지 지원
    if len(options) == 1:
        opt = options[0]
        name_ja = translate_ko_to_ja(opt.get("name", "Option"))
        values = opt.get("values", [])[:20]
        for val in values:
            val_ja = translate_ko_to_ja(val)
            # 옵션명||*옵션값||*추가가격(0)||*재고수량(100)||*판매자코드(빈값)
            parts.append(f"{name_ja}||*{val_ja}||*0||*100||*")
    elif len(options) >= 2:
        opt1 = options[0]
        opt2 = options[1]
        name1_ja = translate_ko_to_ja(opt1.get("name", "Option1"))
        name2_ja = translate_ko_to_ja(opt2.get("name", "Option2"))
        
        vals1 = opt1.get("values", [])[:20]
        vals2 = opt2.get("values", [])[:20]
        
        for v1 in vals1:
            v1_ja = translate_ko_to_ja(v1)
            for v2 in vals2:
                v2_ja = translate_ko_to_ja(v2)
                # 2단계 형식: 명1||*값1||*명2||*값2||*가격||*재고||*코드
                parts.append(f"{name1_ja}||*{v1_ja}||*{name2_ja}||*{v2_ja}||*0||*100||*")
                
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
    """크롤링 결과 → Qoo10 엑셀 업로드 형식 변환 (판매기간 자동 설정 추가)"""
    # 판매 시작일/종료일 계산 (5년 뒤)
    now = datetime.now()
    start_date = now.strftime("%Y-%m-%d")
    end_date = (now + timedelta(days=365 * 5)).strftime("%Y-%m-%d")
    
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
    scraped_brand = product.get("scraped_brand")
    brand_code, cleaned_title_ko = extract_brand_info(raw_title, scraped_brand)
    
    # 3. 사이트별 특수문자 및 불필요 키워드 추가 정제
    title_ko = clean_item_name(cleaned_title_ko)
    print(f"[번역] 상품명 번역 중... ({title_ko[:20]}...)")
    title_ja = translate_ko_to_ja(title_ko)

    # 4. 이미지 처리 (큐텐 업로드를 위해 원본 URL 유지하면서 로컬 가공본 생성)
    main_image_url = product.get("main_image", "")
    try:
        # 큐텐 가이드에 맞춘 가공본은 로컬(outputs/images)에 백업용으로 저장만 합니다.
        make_image_square(main_image_url)
    except Exception as e:
        print(f"[이미지 가공 경고] {e}")
        
    processed_main_image = main_image_url # 엑셀에는 반드시 http:// 주소가 들어가야 함

    additional_images = product.get("additional_images", [])[:50]
    for img_url in additional_images:
        if img_url:
            try:
                make_image_square(img_url)
            except: pass
    
    image_other_str = "$$".join(additional_images) + "$$" if additional_images else ""

    # 5. 옵션 변환 및 번역
    print("[번역] 옵션 번역 중...")
    option_str = format_options_qoo10(product.get("options", []))

    # 6. 카테고리 매칭
    category_id = match_category(raw_title)

    # 7. 무게 정보 처리 (+500g, kg 환산, 0.0 포맷)
    weight_g = product.get("weight", 0.0)
    final_weight_kg = (weight_g + 500) / 1000.0
    weight_str = f"{final_weight_kg:.1f}"

    # 9. 제미나이 프리미엄 상품 설명 생성 (선택 사항)
    print(f"[Gemini] 프리미엄 상품 설명 생성 중... ({title_ko[:20]}...)")
    # 검색 정보 대신 현재 수집된 상품 정보를 기반으로 생성
    gemini_desc = generate_product_description(title_ko)
    
    # 10. 상세페이지 조립 (이미지 추출 + 제미나이 설명 하단 배치)
    only_images = extract_only_images_from_html(product.get("detail_html", ""))
    combined_detail = f"{only_images}<br><br>{gemini_desc}" if gemini_desc else only_images

    return {
        "item_name":            title_ja,  # 번역된 상품명 적용
        "item_promotion_name":  "",
        "item_status_Y/N/D":    "Y",
        "price_yen":            price_jpy,
        "retail_price_yen":     "",
        "taxrate":              10,
        "quantity":             100,
        "option_info":          option_str, # 번역된 옵션 적용

        "image_main_url":       processed_main_image, # 흰색 배경 처리된 이미지 경로 사용
        "image_other_url":      image_other_str,      # 가공된 추가 이미지들 ($$ 구분)

        "item_description":     combined_detail,
        "start_date":           start_date,
        "end_date":             end_date, # 판매종료일 (5년 뒤)
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
        "item_weight":          weight_str, # 무게 정보 (+500g 반영 kg 단위)
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