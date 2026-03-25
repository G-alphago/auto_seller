import requests
from bs4 import BeautifulSoup
import json
import re
import os
import time
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
load_dotenv()

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

    js_data = {}
    js_keys = ["__NEXT_DATA__", "__INITIAL_STATE__", "window.__DATA__", "window.pageData", "dataLayer"]
    for script in soup.find_all("script"):
        text = script.string or ""
        if not text.strip():
            continue
        for key in js_keys:
            if key not in text:
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

    if ld_data.get("name"):
        result["title"] = ld_data["name"]
    else:
        for el in [
            soup.find("meta", property="og:title"),
            soup.find("meta", {"name": "og:title"}),
            soup.find("h1"),
            soup.find("title"),
        ]:
            if el:
                text = el.get("content") or el.get_text(strip=True)
                if text:
                    result["title"] = text
                    break

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
        result["main_image"] = img_val[0] if isinstance(img_val, list) else img_val
    else:
        for el in [
            soup.find("meta", property="og:image"),
            soup.find("meta", {"name": "og:image"}),
            soup.find("meta", {"itemprop": "image"}),
        ]:
            if el and el.get("content"):
                result["main_image"] = el["content"]
                break
        if not result["main_image"]:
            img = (
                soup.find("img", {"id":    re.compile(r'main|product|thumb', re.I)}) or
                soup.find("img", {"class": re.compile(r'main|product|thumb', re.I)})
            )
            if img and img.get("src"):
                src = img["src"]
                result["main_image"] = src if src.startswith("http") else requests.compat.urljoin(url, src)

    options = []

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

    result["options"] = options
    return result


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
                browser = p.chromium.launch(headless=False)
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


def extract_with_playwright(url: str) -> dict:
    from playwright.sync_api import sync_playwright

    SITE_PRICE_SELECTORS = {
        "musinsa.com":      "span.text-body_13px_semi",
        "oliveyoung.co.kr": "span.price",
        "gmarket.co.kr":    "strong.price_real",
        "11st.co.kr":       "div.price",
    }

    SITE_DETAIL_SELECTORS = {
        "smartstore.naver.com": ["div.se-main-container", "div._2kHJS", "div.se-viewer"],
        "oliveyoung.co.kr": ["div.prd-detail", "div#artcInfo", "div.detail-cont"],
        "gmarket.co.kr":    ["div#itemDetailArea", "div.item-detail-area"],
        "11st.co.kr":       ["div#prdDetail", "div#tabDetail", "div.product-detail"],
    }

    detail_html_musinsa = ""

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

            # ── 무신사 전용: JS로 상세 이미지 직접 추출 ──────────────
            if "musinsa.com" in url:
                try:
                    page.evaluate("""
                        () => {
                            const all = document.querySelectorAll('button, a, li');
                            for (const el of all) {
                                const txt = (el.innerText || '').trim();
                                if (txt === '상품정보' || txt === '상세정보') { el.click(); break; }
                            }
                        }
                    """)
                    page.wait_for_timeout(2000)
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
    result = {"title": "", "price": "", "main_image": "", "detail_html": "", "options": []}

    # ── Title ──────────────────────────────────────────────────────────
    for el in [soup.find("meta", property="og:title"), soup.find("meta", {"name": "og:title"}), soup.find("h1")]:
        if el:
            text = el.get("content") or el.get_text(strip=True)
            if text: result["title"] = text; break

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

    try:
        result = extract_product_data(url)
        if is_insufficient(result):
            print("[fallback] Playwright로 재시도...")
            result = extract_with_playwright(url)
    except Exception:
        print("[fallback] requests 실패 → Playwright 시도...")
        result = extract_with_playwright(url)

    return result