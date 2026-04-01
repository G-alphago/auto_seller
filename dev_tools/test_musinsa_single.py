from scraper import extract_product
from converter import convert_to_qoo10_row

url = "https://www.musinsa.com/products/2407421" # MUSINSA Standard product
print(f"Testing Musinsa URL: {url}")
product_data = extract_product(url)
print(f"Extracted Title: {product_data.get('title')}")

# Add brand field manually as scraper doesn't fetch 'scraped_brand' yet (it's often in title)
# But let's see how extract_brand_info deals with it in converter.py
row = convert_to_qoo10_row(product_data)
print(f"Final Brand Code: {row.get('brand_number')}")
print(f"Cleaned Title (JA): {row.get('item_name')}")

print("\n--- Final Detail HTML Snippet ---")
detail = row.get("item_description", "")
print(detail[:1000] + "...")
if "<img>" in detail or "<img" in detail:
    print("\n[SUCCESS] Image tags found in detail.")
if "<a>" in detail or "<a" in detail:
    print("\n[WARNING] Link tags (<a>) still found in detail!")
