import requests
from bs4 import BeautifulSoup
import json
import re
import os
import time
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

# Gemini API 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def extract_weight(text: str) -> float:
    """텍스트에서 무게 정보(g) 추출. 없으면 0.0 반환"""
    if not text: return 0.0
    # 패턴: 숫자 + g 또는 kg (단, ml 등은 제외)
    # 예: 500g, 1.2kg, 1,000g
    # 1. kg 탐지
    kg_match = re.search(r'([\d\.,]+)\s*k?g', text, re.I)
    if kg_match:
        val_str = kg_match.group(1).replace(',', '')
        try:
            val = float(val_str)
            if 'kg' in kg_match.group(0).lower():
                return val * 1000
            return val
        except:
            pass
    return 0.0


def extract_product_data(url: str) -> dict:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }

    result = {
        "title": "",
        "price": "",
        "main_image": "",
        "additional_images": [],
        "detail_html": "",
        "options": []
    }

    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    response.encoding = response.apparent_encoding
    soup = BeautifulSoup(response.text, "html.parser")

def extract_json_by_depth(text, start_char="{"):
    idx = text.find(start_char)
    if idx == -1:
        return None
    open_c  = "{" if start_char == "{" else "["
    close_c = "}" if start_char == "{" else "]"
    depth = 0
    in_string = False
    escape = False
    for i, ch in enumerate(text[idx:], start=idx):
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == open_c:
            depth += 1
        elif ch == close_c:
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[idx:i+1])
                except Exception:
                    return None
    return None

def extract_js_data_from_soup(soup: BeautifulSoup) -> dict:
    js_data = {}
    
    # 1. ID기반 직접 추출 (신속/정확)
    # __NEXT_DATA__
    next_el = soup.find("script", id="__NEXT_DATA__")
    if next_el and next_el.string:
        try:
            s_content = next_el.string.strip()
            try:
                js_data["__NEXT_DATA__"] = json.loads(s_content)
            except:
                import html
                js_data["__NEXT_DATA__"] = json.loads(html.unescape(s_content))
        except: pass
            
    # pdp-data (무신사 최신)
    pdp_el = soup.find("script", id="pdp-data")
    if pdp_el and pdp_el.string:
        try:
            # window.__MSS__.product = { ... }; 또는 state = { ... }; 모두 대응
            m = re.search(r'(?:state|product)\s*=\s*({.*})', pdp_el.string, re.DOTALL)
            if m:
                js_data["pdp_data"] = json.loads(m.group(1))
        except: pass

    # 2. 패턴 기반 추출 (범용)
    js_keys = ["__NEXT_DATA__", "__INITIAL_STATE__", "window.__DATA__", "window.pageData", "dataLayer", "window.v_goodsDetail", "window.prdConfig"]
    for script in soup.find_all("script"):
        text = script.string or ""
        if not text.strip():
            continue
        for key in js_keys:
            if key not in text:
                continue
            # 이미 ID 기반으로 찾은 키면 스킵 (더 정확하므로)
            if key in js_data:
                continue
            key_idx = text.find(key)
            after_key = text[key_idx + len(key):]
            bracket_offset = -1
            for i, ch in enumerate(after_key[:50]):
                if ch in ("{", "["):
                    bracket_offset = i
                    break
            if bracket_offset == -1:
                continue
            snippet = after_key[bracket_offset:]
            parsed = extract_json_by_depth(snippet, snippet[0])
            if parsed and isinstance(parsed, (dict, list)):
                js_data[key] = parsed
    print(f"[DEBUG] Extracted JS Keys: {list(js_data.keys())}")
    return js_data

def extract_product_data(url: str) -> dict:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }

    result = {
        "title": "",
        "price": "",
        "main_image": "",
        "additional_images": [],
        "detail_html": "",
        "options": []
    }

    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    response.encoding = response.apparent_encoding
    soup = BeautifulSoup(response.text, "html.parser")

    js_data = extract_js_data_from_soup(soup)

    ld_data = {}
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            raw = (script.string or "").strip()
            if not raw:
                continue
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                parsed = next(
                    (p for p in parsed if p.get("@type") in ("Product", "Offer")),
                    parsed[0] if parsed else {}
                )
            if parsed.get("@type") == "Product" or "name" in parsed:
                ld_data = parsed
                break
        except Exception:
            continue

    js_data = extract_js_data_from_soup(soup)

    # --- 상품명(Title) 추출 고도화 ---
    candidate_title = ""
    
    # 1. 무신사 전용 셀렉터 (가장 정확)
    if "musinsa.com" in url:
        # 무신사 UI 상의 정확한 제목 엘리먼트
        musinsa_el = (
            soup.select_one("span[class*='GoodsName']") or 
            soup.select_one("div[class*='GoodsName'] span") or
            soup.select_one(".product-detail__items-title") or 
            soup.select_one("h3.product-detail__items-title")
        )
        if musinsa_el:
            candidate_title = musinsa_el.get_text(strip=True)

    # 2. JSON-LD (ld_data)
    if not candidate_title and ld_data.get("name"):
        candidate_title = ld_data["name"]

    # 3. 일반 메타 태그 및 H1, Title tag
    if not candidate_title:
        for el in [
            soup.find("meta", property="og:title"),
            soup.find("meta", {"name": "og:title"}),
            soup.find("h1"),
            soup.find("title"),
        ]:
            if el:
                text = el.get("content") or el.get_text(strip=True)
                if text:
                    candidate_title = text
                    break

    # 4. 범용 접미사 제거 및 정제
    def clean_title_generic(t: str) -> str:
        # 사이트명, 후기 등 흔한 접미사 제거
        t = re.sub(r' - (후기|리뷰|무신사).*$', '', t)
        t = re.sub(r' \| (무신사|올리브영|G마켓|11번가|옥션).*$', '', t)
        t = re.sub(r' : 무신사 스토어.*$', '', t)
        return t.strip()

    result["title"] = clean_title_generic(candidate_title)

    price_patterns = [
        r'[\$₩¥€£][\d,\.]+',
        r'[\d,\.]+\s*원',
        r'[\d,\.]+\s*円',
        r'[\d,\.]+\s*USD',
    ]
    ld_offer = ld_data.get("offers", {})
    if isinstance(ld_offer, list):
        ld_offer = ld_offer[0] if ld_offer else {}
    if ld_offer.get("price"):
        result["price"] = str(ld_offer["price"])
    else:
        price_meta = (
            soup.find("meta", {"property": "product:price:amount"}) or
            soup.find("meta", {"itemprop": "price"})
        )
        if price_meta and price_meta.get("content"):
            result["price"] = price_meta["content"]
        else:
            for sel in [
                {"class": re.compile(r'price', re.I)},
                {"id":    re.compile(r'price', re.I)},
                {"itemprop": "price"},
            ]:
                el = soup.find(attrs=sel)
                if el:
                    txt = el.get_text(strip=True)
                    for pat in price_patterns:
                        m = re.search(pat, txt)
                        if m:
                            result["price"] = m.group()
                            break
                if result["price"]:
                    break
            if not result["price"]:
                for pat in price_patterns:
                    m = re.search(pat, soup.get_text(" "))
                    if m:
                        result["price"] = m.group()
                        break

    if ld_data.get("image"):
        img_val = ld_data["image"]
        if isinstance(img_val, list):
            result["main_image"] = img_val[0]
            result["additional_images"] = img_val[1:]
        else:
            result["main_image"] = img_val
    else:
        for el in [
            soup.find("meta", property="og:image"),
            soup.find("meta", {"name": "og:image"}),
            soup.find("meta", {"itemprop": "image"}),
        ]:
            if el and el.get("content"):
                result["main_image"] = el["content"]
                break
        
        # 추가 이미지 셀렉터 (무신사 등)
        gallery_imgs = soup.select("div.thumb img, .product-detail__items-images img, #product_images img")
        for g_img in gallery_imgs:
            src = g_img.get("src") or g_img.get("data-src")
            if src:
                full_url = src if src.startswith("http") else requests.compat.urljoin(url, src)
                if full_url not in result["additional_images"] and full_url != result["main_image"]:
                    result["additional_images"].append(full_url)

        if not result["main_image"]:
            img = (
                soup.find("img", {"id":    re.compile(r'main|product|thumb', re.I)}) or
                soup.find("img", {"class": re.compile(r'main|product|thumb', re.I)})
            )
            if img and img.get("src"):
                src = img["src"]
                result["main_image"] = src if src.startswith("http") else requests.compat.urljoin(url, src)

    result["options"] = parse_options(url, soup, js_data)
    return result


def get_musinsa_options(product_id: str) -> list:
    """무신사 옵션 API 직접 호출 (가장 정확)"""
    options = []
    # CLOTHES가 기본이나, 실패시 다른 코드도 고려 가능
    for kind in ["CLOTHES", "GOODS"]:
        api_url = f"https://goods-detail.musinsa.com/api2/goods/{product_id}/options?goodsSaleType=SALE&optKindCd={kind}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": f"https://www.musinsa.com/products/{product_id}",
            "Accept": "application/json"
        }
        try:
            resp = requests.get(api_url, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                basic = data.get("basic", [])
                if not basic: continue
                
                for opt in basic:
                    name = opt.get("name")
                    vals = [v.get("name") for v in opt.get("optionValues", []) if not (v.get("isSoldOut") or "품절" in v.get("name", ""))]
                    if name and vals:
                        options.append({"name": name, "values": vals})
                if options: break
        except: pass
    return options

def parse_options(url: str, soup: BeautifulSoup, js_data: dict) -> list:
    """사이트별 옵션 추출 로직 통합"""
    options = []

    # 1. 무신사 (API 우선, NEXT_DATA/pdp-data 백업)
    if "musinsa.com" in url:
        try:
            # 0단계: API 시도
            m_id = re.search(r'/products/(\d+)', url)
            if m_id:
                options = get_musinsa_options(m_id.group(1))
            
            if not options:
                # 1단계: NEXT_DATA 시도
                next_data = js_data.get("__NEXT_DATA__", {})
                ms_options = next_data.get("props", {}).get("pageProps", {}).get("productView", {}).get("options", [])
                
                if not ms_options:
                    initial_state = next_data.get("props", {}).get("pageProps", {}).get("initialState", {})
                    ms_options = initial_state.get("goodsDetail", {}).get("goodsOption", {}).get("options", [])

                if not ms_options:
                    initial_state = next_data.get("props", {}).get("pageProps", {}).get("initialState", {})
                    ms_options = initial_state.get("goodsOption", {}).get("options", [])

                # 2단계: pdp-data 시도
                if not ms_options:
                    pdp_data = js_data.get("pdp_data", {})
                    ms_options = pdp_data.get("options", [])

                for opt in ms_options:
                    opt_name = opt.get("name") or opt.get("optionName") or "옵션"
                    raw_vals = opt.get("values") or opt.get("optionValues") or []
                    opt_vals = []
                    for v in raw_vals:
                        val_txt = v.get("name") or v.get("text") or v.get("optionValueName") or str(v)
                        # 품절 여부 체크
                        is_sold_out = v.get("isSoldOut", False) or v.get("stockStatus") == "out_of_stock"
                        if val_txt and "(품절)" not in val_txt and not is_sold_out:
                            opt_vals.append(val_txt.strip())
                    if opt_vals:
                        options.append({"name": opt_name, "values": opt_vals})
            print(f"[DEBUG] Musinsa Options Found: {len(options)}")
        except Exception as e:
            print(f"[DEBUG] Musinsa Error: {e}")
            pass

    # 2. 11번가 (ProductData 또는 prdConfig)
    elif "11st.co.kr" in url:
        prd_config = js_data.get("window.prdConfig", {})
        opt_list_data = prd_config.get("optionList", [])
        
        if opt_list_data:
            for opt in opt_list_data:
                name = opt.get("optionName") or "옵션"
                vals = [v.get("optionValueName") for v in opt.get("optionValueList", []) if v.get("stockQty", 0) > 0]
                if name and vals:
                    options.append({"name": name, "values": vals})
        
        if not options:
            # (기존 로직 유지)
            for script in soup.find_all("script"):
                txt = script.string or ""
                if "prdNo" in txt and "optionList" in txt:
                    try:
                        m = re.search(r'optionList\s*:\s*(\[.*?\])\s*,', txt, re.DOTALL)
                        if m:
                            raw_opts = json.loads(m.group(1))
                            for opt in raw_opts:
                                name = opt.get("optNm") or "옵션"
                                vals = [v.get("optValueNm") for v in opt.get("optValueList", []) if v.get("stckQty", 0) > 0]
                                if name and vals:
                                    options.append({"name": name, "values": vals})
                    except: pass
                    break

        if not options:
            # DOM 기반 (사이드바 드롭다운 등)
            for drop in soup.select(".accordion_body.dropdown_list, .c_product_option_list, .dropdown_list"):
                btns = drop.select("button.c_product_btn_select, .option_item, .dropdown_item button")
                if btns:
                    vals = []
                    for b in btns:
                        txt = b.get_text(strip=True).replace("선택하기", "").replace("판매가", "").replace("품절", "")
                        txt = re.sub(r'[\d,]+원', '', txt).strip()
                        if txt: vals.append(txt)
                    if vals:
                        options.append({"name": "옵션", "values": vals})

    # 3. 올리브영 (Playwright 직접 추출 우선, 없으면 DOM 기반)
    elif "oliveyoung.co.kr" in url:
        # Playwright에서 직접 추출된 옵션이 있으면 최우선 사용
        direct_opts = js_data.get("oliveyoung_options", [])
        if direct_opts:
            options.append({"name": "옵션", "values": list(dict.fromkeys(direct_opts))})
        else:
            # DOM 기반 fallback (정교한 셀렉터: 버튼만 타겟팅)
            opt_list = soup.select("button.OptionSelector_option-item-btn__yq5_A, button[class*='OptionSelector_option-item-btn'], button[class*='option-item-btn']")
            
            if not opt_list:
                opt_list = soup.select(".pkg_info .name, .goods_option_area .name, .pkg-info .name")
                
            vals = []
            for btn in opt_list:
                name_el = btn.select_one("span > span:nth-child(2) > span:first-child")
                if name_el:
                    val = name_el.get_text(strip=True)
                else:
                    val = btn.get_text(" ", strip=True)
                
                val = re.sub(r'\[.*?\]', '', val)
                val = re.sub(r'[\d,]+원', '', val)
                val = val.replace("오늘드림", "").replace("품절", "").strip()
                val = re.sub(r'\s+', ' ', val).strip()
                
                if val and val not in vals and val not in ["옵션을 선택해 주세요", "선택"]:
                    vals.append(val)
            
            if vals:
                options.append({"name": "옵션", "values": list(dict.fromkeys(vals))})

    # 4. 범용
    if not options:
        def flatten_option_values(raw_values):
            result_vals = []
            for item in raw_values:
                if isinstance(item, str) and item.strip():
                    result_vals.append(item.strip())
                elif isinstance(item, dict):
                    for key in ("name", "label", "value", "title", "text"):
                        v = item.get(key)
                        if v and isinstance(v, str) and v.strip():
                            result_vals.append(v.strip())
                            break
                elif isinstance(item, list):
                    for sub in item:
                        if isinstance(sub, str) and sub.strip():
                            result_vals.append(sub.strip())
                        elif isinstance(sub, dict):
                            for key in ("name", "label", "value", "title", "text"):
                                v = sub.get(key)
                                if v and isinstance(v, str) and v.strip():
                                    result_vals.append(v.strip())
                                    break
            return list(dict.fromkeys(result_vals))

        for sel in soup.find_all("select"):
            label = soup.find("label", {"for": sel.get("id")})
            opt_name = label.get_text(strip=True) if label else (sel.get("name") or sel.get("id") or "option")
            values = [
                o.get_text(strip=True)
                for o in sel.find_all("option")
                if o.get_text(strip=True) and o.get("value") not in ("", None, "0", "-1")
            ]
            if values:
                options.append({"name": opt_name, "values": values})

        if not options:
            for ul in soup.find_all("ul", {"class": re.compile(r'option|variant|swatch|color|size', re.I)}):
                items = [li.get_text(strip=True) for li in ul.find_all("li") if li.get_text(strip=True)]
                if items:
                    options.append({"name": " ".join(ul.get("class", ["option"])), "values": items})

        if not options:
            for group in soup.find_all(attrs={"class": re.compile(r'option|variant|swatch', re.I)}):
                buttons = group.find_all(["button", "span", "a", "li"])
                values = list(dict.fromkeys(b.get_text(strip=True) for b in buttons if b.get_text(strip=True)))
                if len(values) > 1:
                    label_el = group.find_previous(["label", "dt", "th", "span"])
                    opt_name = label_el.get_text(strip=True) if label_el else "option"
                    options.append({"name": opt_name, "values": values})
                    break

        if not options:
            def find_options_in_js(obj, depth=0):
                if depth > 6:
                    return None
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if any(kw in k.lower() for kw in ["option", "variant", "attribute", "spec"]):
                            if isinstance(v, list) and v:
                                cleaned = flatten_option_values(v)
                                if cleaned:
                                    return [{"name": k, "values": cleaned}]
                            elif isinstance(v, dict) and v:
                                return [{"name": k, "values": list(v.keys())}]
                        found = find_options_in_js(v, depth + 1)
                        if found:
                            return found
                elif isinstance(obj, list):
                    for item in obj:
                        found = find_options_in_js(item, depth + 1)
                        if found:
                            return found
                return None

            for key, data in js_data.items():
                hit = find_options_in_js(data)
                if hit:
                    options = hit
                    break
    
    return options


def extract_with_naver_api(url: str) -> dict:
    client_id     = os.getenv("NAVER_CLIENT_ID", "")
    client_secret = os.getenv("NAVER_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        raise ValueError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수가 없습니다.")

    product_id = ""
    m = re.search(r'/products/(\d+)', url)
    if m:
        product_id = m.group(1)

    store_m = re.search(r'smartstore\.naver\.com/([^/]+)/', url)
    store   = store_m.group(1) if store_m else ""

    api_headers = {
        "X-Naver-Client-Id":     client_id,
        "X-Naver-Client-Secret": client_secret,
    }

    def search_naver(query: str, display: int = 5) -> list:
        resp = requests.get(
            "https://openapi.naver.com/v1/search/shop.json",
            headers=api_headers,
            params={"query": query, "display": display, "sort": "sim"},
            timeout=10
        )
        resp.raise_for_status()
        return resp.json().get("items", [])

    def strip_tags(text):
        return re.sub(r'<[^>]+>', '', text or "").strip()

    items = []
    if product_id:
        items = search_naver(product_id)
    if not items and store:
        items = search_naver(store)

    if not items:
        try:
            print("[naver api] 상품명 추출 시도 (Playwright)...")
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    locale="ko-KR",
                )
                page = context.new_page()
                page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(3000)
                title_js = page.evaluate("""
                    () => {
                        const og = document.querySelector('meta[property="og:title"]');
                        if (og) return og.content;
                        const h1 = document.querySelector('h1');
                        if (h1) return h1.innerText;
                        return document.title;
                    }
                """)
                browser.close()
            if title_js and "에러" not in title_js:
                print(f"[naver api] 상품명으로 검색: {title_js[:30]}")
                items = search_naver(title_js[:50])
        except Exception as e:
            print(f"[naver api] Playwright 상품명 추출 실패: {e}")

    if not items:
        raise ValueError("네이버 API 검색 결과 없음")

    best = items[0]
    if store:
        for item in items:
            if store.lower() in item.get("link", "").lower() or \
               store.lower() in item.get("mallName", "").lower():
                best = item
                break

    title      = strip_tags(best.get("title", ""))
    price      = best.get("lprice", "") or best.get("hprice", "")
    main_image = best.get("image", "")
    link       = best.get("link", url)

    detail_html = f"""<div>
        <h2>{title}</h2>
        <p>価格: {price}円</p>
        <img src="{main_image}" alt="{title}" style="max-width:100%" />
        <p>商品リンク: <a href="{link}">{link}</a></p>
    </div>"""

    return {
        "title":       title,
        "price":       price,
        "main_image":  main_image,
        "detail_html": detail_html.strip(),
        "options":     []
    }


def generate_product_description(title: str, additional_info: str = "") -> str:
    """상품명을 기반으로 일본어 상품 소개 및 사용법 HTML 생성 (모던 테마 적용)"""
    if not GEMINI_API_KEY or not title:
        return ""

    prompt = f"""
    당신은 일본 시장을 전문으로 하는 이커머스 MD입니다.
    한국의 상품 정보(제목, 특징)를 바탕으로 일본 구매자에게 매력적인 상세 페이지 섹션을 일본어로 생성해주세요.
    
    [상품 정보]
    상품명: {title}
    추가 정보: {additional_info}
    
    [요구 사항]
    1. 언어: 일본어 (자연스럽고 정중한 Desu/Masu 스타일)
    2. 구성:
       - [Introduction]: 캐치프레이즈와 상품의 가치 제안.
       - [Key Features]: 상품의 3가지 주요 특징 (아이콘 또는 글머리 기호 사용).
       - [How to Use]: 상세한 단계별 사용 방법.
       - [Why You'll Love It]: 구매를 유도하는 마무리 멘트.
    3. 형식: 순수 HTML (<div> 구조). Markdown 코드 블록 없이 결과만 출력하세요.
    4. 제한 사항: **절대로 <a> (링크) 태그나 <script> 태그를 포함하지 마세요.** 오직 텍스트와 레이아웃용 태그(div, h2, h3, p, ul, li, br)만 사용하세요.
    5. 디자인 (모던 프리미엄 테마):
       - 폰트: 'Noto Sans JP', sans-serif (일본 표준 폰트).
       - 색상: 화이트에서 연한 그레이(#F9FAFB)로 이어지는 은은한 그라데이션 배경.
       - 포인트 컬러: 세련된 차콜(#333333) 및 부드러운 포인트 색상.
       - 레이아웃: 좌우 여백 20px, 상하 여백 40px, 둥근 테두리(12px).
       - 모바일 대응: max-width: 100% 적용.
    """

    try:
        model = genai.GenerativeModel('gemini-2.5-flash') # 할당량 넉넉한 2.5-flash 모델 사용
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        if content.startswith("```html"):
            content = content.replace("```html", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()
            
        return content
    except Exception as e:
        print(f"[Gemini Error] 상품 설명 생성 실패: {e}")
        return ""


def extract_with_playwright(url: str) -> dict:
    from playwright.sync_api import sync_playwright

    SITE_PRICE_SELECTORS = {
        "musinsa.com":      "span.text-body_13px_semi",
        "oliveyoung.co.kr": "span.price",
        "gmarket.co.kr":    "strong.price_real",
        "11st.co.kr":       ".price_real .value, div.price",
    }

    SITE_DETAIL_SELECTORS = {
        "smartstore.naver.com": ["div.se-main-container", "div._2kHJS", "div.se-viewer"],
        "oliveyoung.co.kr": ["div.prd-detail", "div#artcInfo", "div.detail-cont"],
        "gmarket.co.kr":    ["div#itemDetailArea", "div.item-detail-area"],
        "11st.co.kr":       ["#tabpanelDetail1", ".prdc_detail_area", "div#prdDetail", "div#tabDetail", "div.product-detail"],
    }

    detail_html_musinsa = ""
    oy_options_direct = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ]
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="ko-KR",
            timezone_id="Asia/Seoul"
        )
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
        
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # 11st 등의 동적 페이지를 위한 추가 대기
            if "11st.co.kr" in url:
                try:
                    page.wait_for_selector(".c_product_info_title h1, h1.title", timeout=5000)
                except: pass
            
            # Olive Young: 옵션 버튼 클릭 및 직접 텍스트 추출
            if "oliveyoung.co.kr" in url:
                # 동적 로딩을 위한 대기 시간 추가 (debug 결과 3초 필요)
                page.wait_for_timeout(3000)
                try:
                    print("[DEBUG] Olive Young: 옵션 버튼 찾는 중...")
                    # '선택해 주세요' 텍스트를 포함하는 버튼 클릭
                    clicked = page.evaluate("""
                        () => {
                            const btns = Array.from(document.querySelectorAll('button'));
                            const optBtn = btns.find(b => b.innerText && b.innerText.includes('선택해 주세요'));
                            if (optBtn) {
                                optBtn.click();
                                return true;
                            }
                            return false;
                        }
                    """)
                    
                    if clicked:
                        print("[DEBUG] Olive Young: 옵션 버튼 클릭 성공. 대기 중...")
                        page.wait_for_timeout(3000)
                        
                        # 옵션 항목 로딩 대기
                        try:
                            page.wait_for_selector('button[class*="OptionSelector_option-item-btn"]', timeout=5000)
                        except:
                            print("[DEBUG] Olive Young: 옵션 항목 셀렉터 대기 타임아웃")
                        
                        # Playwright에서 직접 옵션 텍스트 추출
                        oy_options = page.evaluate("""
                            () => {
                                const btns = document.querySelectorAll('button[class*="OptionSelector_option-item-btn"]');
                                if (!btns.length) return [];
                                return Array.from(btns).map(b => {
                                    const nameEl = b.querySelector('span > span:nth-child(2) > span:first-child') || b;
                                    let txt = nameEl.innerText || b.innerText;
                                    txt = txt.replace(/\\[.*?\\]/g, '');
                                    txt = txt.replace(/[\\d,]+원/g, '');
                                    txt = txt.replace(/오늘드림/g, '').replace(/품절/g, '');
                                    txt = txt.replace(/\\s+/g, ' ').trim();
                                    return txt;
                                }).filter(t => t && t.length > 0);
                            }
                        """)
                        
                        if oy_options:
                            oy_options_direct = oy_options
                            print(f"[DEBUG] Olive Young 옵션 직접 추출 성공: {len(oy_options)}개")
                        else:
                            print("[DEBUG] Olive Young: 옵션 버튼은 클릭했으나 항목 추출 실패")
                    else:
                        print("[DEBUG] Olive Young: '선택해 주세요' 버튼을 찾지 못함")
                    
                except Exception as e:
                    print(f"[DEBUG] Olive Young Playwright Interaction Exception: {e}")

            # ── 브랜드 수집 (사이트별) ──
            scraped_brand_val = ""
            current_url = page.url
            is_redirected = "products/" not in current_url and "musinsa.com" in url
            
            if is_redirected:
                print(f"[DEBUG] 리다이렉트 감지: {url} -> {current_url} (품절/비공개 예상)")
                if "recommend" in current_url:
                    html = "<html><body>PRODUCT_NOT_FOUND</body></html>"
            else:
                try:
                    if "musinsa.com" in url:
                        # 1. JS 객체 직접 접근 (window.__NEXT_DATA__의 goodsDetail이 가장 정확함)
                        scraped_brand_val = page.evaluate("""
                            () => {
                                try {
                                    const nextData = window.__NEXT_DATA__ || {};
                                    const gd = nextData.props.pageProps.goodsDetail || {};
                                    if (gd.brandEnglishNm) return gd.brandEnglishNm;
                                    if (gd.brandNm) return gd.brandNm;

                                    const mss = window.__MSS__ || {};
                                    const productState = (mss.product && mss.product.state) || {};
                                    const bi = productState.brandInfo || {};
                                    if (bi.brandEnglishName) return bi.brandEnglishName;
                                    if (bi.brandName) return bi.brandName;

                                    const pv = nextData.props.pageProps.productView || {};
                                    const b = pv.brandInfo || {};
                                    return b.nameEn || b.nameKo || pv.brandName || '';
                                } catch(e) { return ''; }
                            }
                        """)
                    
                    if not scraped_brand_val:
                        if "musinsa.com" in url:
                            scraped_brand_val = page.evaluate("""
                                () => {
                                    const b1 = document.querySelector('.gtm-click-brand');
                                    if (b1 && b1.innerText.trim()) return b1.innerText.trim();
                                    const b2 = document.querySelector('a[href*="/brand/"]');
                                    if (b2 && b2.innerText.trim()) return b2.innerText.trim();
                                    const b3 = document.querySelector('[class*="BrandLink"], [class*="BrandName"], .product-detail__brand-name');
                                    if (b3 && b3.innerText.trim()) return b3.innerText.trim();
                                    return '';
                                }
                            """)
                        elif "oliveyoung.co.kr" in url:
                            scraped_brand_val = page.evaluate("""
                                () => {
                                    const b = document.querySelector('.brand_name, p.prd_brand, .brand-title');
                                    return b ? b.innerText.trim() : '';
                                }
                            """)

                    # [브랜드 정제 규칙] 한글/영문 혼용 시 영문만 추출, 영문이 없으면 한글
                    if scraped_brand_val:
                        # 1. 괄호 안 영문 추출 시도
                        match_in = re.search(r'\(([^)]+)\)', scraped_brand_val)
                        # 2. 괄호 밖 영문 추출 시도 (괄호 밖이 영문인 경우)
                        match_out = re.search(r'^([a-zA-Z0-9\s&]+)\(', scraped_brand_val)
                        
                        if match_in and re.search(r'[a-zA-Z]', match_in.group(1)):
                            scraped_brand_val = match_in.group(1).strip()
                        elif match_out and re.search(r'[a-zA-Z]', match_out.group(1)):
                            scraped_brand_val = match_out.group(1).strip()
                        elif re.search(r'[a-zA-Z]', scraped_brand_val):
                            # 한글 제거하고 영문/숫자/공백 등만 남김
                            scraped_brand_val = re.sub(r'[ㄱ-ㅎㅏ-ㅣ가-힣]', '', scraped_brand_val).strip()

                    if scraped_brand_val:
                        print(f"[DEBUG] {url} 브랜드 수집 최종: {scraped_brand_val}")
                except Exception as e:
                    print(f"[DEBUG] 브랜드 수집 중 오류: {e}")

            page.wait_for_timeout(2000)

            # ── 전체 페이지 스크롤 로직 (숨겨진 이미지 지연 로딩 해제) ──
            page.evaluate("""
                async () => {
                    await new Promise((resolve) => {
                        let totalHeight = 0;
                        let distance = 400; // 한 번에 내릴 픽셀
                        let timer = setInterval(() => {
                            let scrollHeight = document.body.scrollHeight;
                            window.scrollBy(0, distance);
                            totalHeight += distance;

                            // 끝까지 스크롤했거나 15번 이상 내렸으면 종료
                            if(totalHeight >= scrollHeight - window.innerHeight || totalHeight > 15000){
                                clearInterval(timer);
                                resolve();
                            }
                        }, 150); // 0.15초마다 스크롤
                    });
                }
            """)
            page.wait_for_timeout(2000) # 스크롤 후 이미지가 뜰 때까지 잠시 대기

            # ── 무신사 전용: '더보기' 버튼 클릭 및 상세 이미지 추출 ──────────────
            if "musinsa.com" in url:
                try:
                    # 1. 상세정보 탭 클릭
                    page.evaluate("""
                        () => {
                            const all = document.querySelectorAll('button, a, li');
                            for (const el of all) {
                                const txt = (el.innerText || '').trim();
                                if (txt === '상품정보' || txt === '상세정보') { el.click(); break; }
                            }
                        }
                    """)
                    page.wait_for_timeout(1000)
                    
                    # 2. '더보기' 버튼 클릭 (텍스트 기반)
                    page.evaluate("""
                        () => {
                            const btns = Array.from(document.querySelectorAll('button'));
                            const moreBtn = btns.find(b => b.innerText && (b.innerText.includes('상품 정보 더보기') || b.innerText.includes('상세정보 더보기')));
                            if (moreBtn) moreBtn.click();
                        }
                    """)
                    page.wait_for_timeout(2000)

                    # 3. 상세 이미지 추출
                    detail_imgs = page.evaluate("""
                        () => {
                            const imgs = [];
                            document.querySelectorAll('img').forEach(img => {
                                const src = img.src || '';
                                if (!src || src.startsWith('data:')) return;
                                if (src.includes('prd_img') && src.includes('detail_')) {
                                    imgs.push(src.replace('_500.', '_big.').split('?')[0]);
                                }
                            });
                            return [...new Set(imgs)];
                        }
                    """)
                    if detail_imgs:
                        detail_html_musinsa = "<div>" + "".join(
                            f'<img src="{src}" style="max-width:100%;display:block;margin:0 auto;" />'
                            for src in detail_imgs
                        ) + "</div>"
                except Exception as e:
                    print(f"[무신사 상세] 추출 실패: {e}")

            html = page.content()
        finally:
            browser.close()

    soup = BeautifulSoup(html, "html.parser")
    js_data = extract_js_data_from_soup(soup)
    if oy_options_direct:
        js_data["oliveyoung_options"] = oy_options_direct

    # 추가 이미지(갤러리) 수집 로직
    additional_images = []
    # 갤러리/썸네일 이미지 추출 (Playwright가 렌더링한 최종 DOM에서)
    img_selectors = [
        ".Pagination__PaginationContainer-sc-1yn5os-1 img", # 무신사 썸네일
        "div.thumb img", ".product-detail__items-images img", 
        "#product_images img", ".prd_img_area img", ".c_product_view_img img"
    ]
    for sel in img_selectors:
        for img in soup.select(sel):
            src = img.get("src") or img.get("data-src") or img.get("data-original")
            if src:
                # 썸네일의 경우 큰 이미지로 변환 시도 (무신사 특화)
                if "musinsa.com" in url and ("_small" in src or "_60." in src):
                    src = src.replace("_small", "_big").replace("_60.", "_500.")
                
                full_url = requests.compat.urljoin(url, src)
                if full_url not in additional_images:
                    additional_images.append(full_url)

    result = {
        "title": "",
        "price": "",
        "main_image": "",
        "additional_images": additional_images,
        "scraped_brand": scraped_brand_val, # 수집된 브랜드명 추가
        "detail_html": "",
        "options": parse_options(url, soup, js_data)
    }

    candidate_title = ""
    if "musinsa.com" in url:
        # window.__NEXT_DATA__.props.pageProps.goodsDetail.goodsNm 이 가장 정확함
        mss_goods_nm = ""
        try:
            next_data = js_data.get("__NEXT_DATA__", {})
            mss_goods_nm = next_data.get("props", {}).get("pageProps", {}).get("goodsDetail", {}).get("goodsNm", "")
            if not mss_goods_nm:
                mss = js_data.get("__MSS__", {})
                mss_goods_nm = mss.get("product", {}).get("state", {}).get("goodsNm", "")
        except: pass
        
        if not mss_goods_nm:
            musinsa_el = (
                soup.select_one("span[class*='GoodsName']") or 
                soup.select_one("div[class*='GoodsName'] span") or
                soup.select_one(".product-detail__items-title") or 
                soup.select_one("h3.product-detail__items-title") or
                soup.select_one("div.FixedArea__Container h3") or
                soup.select_one("h3")
            )
            candidate_title = musinsa_el.get_text(strip=True) if musinsa_el else ""
        else:
            candidate_title = mss_goods_nm
            
    # 11st 지원 추가
    if not candidate_title and "11st.co.kr" in url:
        st11_el = soup.select_one(".c_product_info_title h1") or soup.select_one("h1.title")
        if st11_el:
            candidate_title = st11_el.get_text(strip=True)

    if not candidate_title:
        for el in [soup.find("meta", property="og:title"), soup.find("meta", {"name": "og:title"}), soup.find("h1")]:
            if el:
                text = el.get("content") or el.get_text(strip=True)
                if text:
                    candidate_title = text
                    break

    def clean_title_generic(t: str) -> str:
        t = re.sub(r' - (후기|리뷰|무신사).*$', '', t)
        t = re.sub(r' \| (무신사|올리브영|G마켓|11번가|옥션).*$', '', t)
        t = re.sub(r' : 무신사 스토어.*$', '', t)
        return t.strip()

    result["title"] = clean_title_generic(candidate_title)

    # ── Price ──────────────────────────────────────────────────────────
    price = ""
    for domain, selector in SITE_PRICE_SELECTORS.items():
        if domain in url:
            el = soup.select_one(selector)
            if el:
                m = re.search(r'[\d,]+', el.get_text(strip=True))
                if m: price = m.group().replace(",", "") + "원"
            break
    if not price:
        price_meta = soup.find("meta", {"property": "product:price:amount"})
        if price_meta and price_meta.get("content"): price = price_meta["content"]
    
    if not price:
        skip_kw = ['배송', '할인', '쿠폰', '적립', '포인트', '무료', '이상']
        for el in soup.find_all(True):
            if el.find(): continue
            txt = el.get_text(strip=True)
            if not re.search(r'\d{3,}[,\d]*원', txt) or len(txt) > 20 or any(kw in txt for kw in skip_kw): continue
            m = re.search(r'[\d,]+원', txt)
            if m:
                price = m.group()
                break
    result["price"] = price

    # ── Main Image ──────────────────────────────────────────────────────
    for el in [soup.find("meta", property="og:image"), soup.find("meta", {"name": "og:image"})]:
        if el and el.get("content"):
            result["main_image"] = el["content"]
            break
            
    if not result["main_image"] and "11st.co.kr" in url:
        st11_img = soup.select_one(".c_product_view_img img") or soup.select_one("#productImg img")
        if st11_img:
            result["main_image"] = st11_img.get("src") or st11_img.get("data-src")

    # ── Detail HTML 필터 강화 ───────────────────────────────────────
    # payment, benefit, policy 등 상세페이지가 아닌 부분을 강력하게 제외
    SKIP = re.compile(
        r'review|recommend|footer|nav|header|menu|banner|gnb|lnb|payment|benefit|'
        r'login|similar|carousel|__next|policy|notice', re.I
    )

    def is_skip(tag):
        combined = " ".join(tag.get("class", [])) + (tag.get("id") or "")
        return bool(SKIP.search(combined))

    detail_html = ""

    # 1. 무신사 전용
    if "musinsa.com" in url and detail_html_musinsa:
        detail_html = detail_html_musinsa

    # 2. 사이트별 전용 셀렉터
    if not detail_html:
        for domain, selectors in SITE_DETAIL_SELECTORS.items():
            if domain in url:
                for selector in selectors:
                    el = soup.select_one(selector)
                    if el and len(str(el)) > 200:
                        detail_html = str(el)
                        break
                break

    # 3. 일반 패턴
    if not detail_html:
        for sel in [
            {"id":    re.compile(r'detail|description|content|spec', re.I)},
            {"class": re.compile(r'detail|description|product[-_]?desc', re.I)},
        ]:
            el = soup.find(attrs=sel)
            if el and not is_skip(el) and len(str(el)) > 200:
                detail_html = str(el)
                break

    # 4. 이미지 비중 높은 블록 탐색 (Fallback)
    if not detail_html:
        candidates = []
        for tag in soup.find_all(["div", "section"]):
            if is_skip(tag): continue
            html_str = str(tag)
            if len(html_str) < 500 or len(html_str) > len(html) * 0.6: continue
            img_count = len(tag.find_all("img"))
            text_len  = len(tag.get_text(strip=True))
            score = img_count * 500 + text_len
            candidates.append((score, html_str))
        if candidates:
            candidates.sort(reverse=True)
            detail_html = candidates[0][1]

    # 상세 설명에서 무게 정보 추출 시도
    if detail_html:
        weight_val = extract_weight(BeautifulSoup(detail_html, 'html.parser').get_text())
        result["weight"] = weight_val
    else:
        result["weight"] = 0.0

    result["detail_html"] = detail_html
    return result


def extract_product(url: str) -> dict:
    def is_insufficient(r):
        return (
            not r.get("title") or
            not r.get("price") or
            len(r.get("detail_html", "")) < 500
        )

    is_naver = "smartstore.naver.com" in url or "naver.com" in url

    if is_naver:
        try:
            print("[naver api] 네이버 API로 시도...")
            result = extract_with_naver_api(url)
            if result.get("title") and result.get("price") and "img" in result.get("detail_html", ""):
                return result
            print("[naver api] 데이터 부족 → Playwright fallback")
        except Exception as e:
            print(f"[naver api] 실패: {e} → Playwright fallback")
        return extract_with_playwright(url)

    # 올리브영은 동적 옵션 로딩 필요 → 항상 Playwright 사용
    if "oliveyoung.co.kr" in url:
        return extract_with_playwright(url)

    try:
        result = extract_product_data(url)
        if is_insufficient(result):
            print("[fallback] Playwright로 재시도...")
            result = extract_with_playwright(url)
    except Exception:
        print("[fallback] requests 실패 → Playwright 시도...")
        result = extract_with_playwright(url)

    return result