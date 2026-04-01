import requests
import json

product_id = "2407421"
# API URL (optKindCd might vary, but CLOTHES is common)
api_url = f"https://goods-detail.musinsa.com/api2/goods/{product_id}/options?goodsSaleType=SALE&optKindCd=CLOTHES"

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": f"https://www.musinsa.com/products/{product_id}",
    "Accept": "application/json"
}

print(f"Testing Musinsa API: {api_url}")
try:
    resp = requests.get(api_url, headers=headers, timeout=10)
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Data Keys: {data.keys()}")
        if "data" in data and "basic" in data["data"]:
            options = []
            for opt in data["data"]["basic"]:
                name = opt.get("name")
                values = [v.get("name") for v in opt.get("optionValues", [])]
                options.append({"name": name, "values": values})
            print(f"Extracted Options: {options}")
        else:
            print("Structure mismatch or unexpected response.")
            print(json.dumps(data, indent=2)[:1000])
    else:
        print(f"Failed to fetch: {resp.text[:500]}")
except Exception as e:
    print(f"Error: {e}")
