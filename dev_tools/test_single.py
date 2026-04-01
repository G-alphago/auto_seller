from classifier import match_category
from scraper import extract_product
from converter import convert_to_qoo10_row

url = "https://www.11st.co.kr/products/6451634676"  # Valid 11st URL (Yonex Power Cushion Lumio 4)
print(f"Testing URL: {url}")
product_data = extract_product(url)
print(f"Extracted Title: {product_data.get('title')}")

cat_code = match_category(product_data.get("title"))
print(f"Matched Category Code: {cat_code}")

row = convert_to_qoo10_row(product_data)
print(f"Final Category in Row: {row.get('category_number')}")
