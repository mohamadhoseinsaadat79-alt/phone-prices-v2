#!/usr/bin/env python3
"""
ردیاب قیمت گوشی - نسخه ساده و پایدار
خروجی مستقیم HTML برای GitHub Pages
"""
import json
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

# تنظیمات
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
}

PRICE_MIN_TOMAN = 800_000
PRICE_MAX_TOMAN = 999_999_999
PRICE_TOKEN_RE = re.compile(r"([\d۰-۹]{1,3}(?:[,\u066c٬،][\d۰-۹]{3})+)")

def normalize_digits(text: str) -> str:
    """تبدیل اعداد فارسی و عربی به انگلیسی"""
    en = "0123456789"
    fa = "۰۱۲۳۴۵۶۷۸۹"
    ar = "٠١٢٣٤٥٦٧٨٩"
    for e, f in zip(en, fa):
        text = text.replace(f, e)
    for e, a in zip(en, ar):
        text = text.replace(a, e)
    return text

def parse_price_token(raw: str):
    """تجزیه قیمت از متن"""
    cleaned = normalize_digits(raw).replace(",", "").replace(".", "").replace("٬", "").replace("،", "")
    if not cleaned.isdigit():
        return None
    return int(cleaned)

def extract_price_from_text(text: str, min_price: int = PRICE_MIN_TOMAN, max_price: int = PRICE_MAX_TOMAN):
    """استخراج اولین قیمت معقول از متن"""
    for match in PRICE_TOKEN_RE.finditer(text):
        price = parse_price_token(match.group(1))
        if price and min_price <= price <= max_price:
            return price
    return None

def extract_product_link(html: str, site_name: str) -> str:
    """استخراج لینک مستقیم محصول"""
    soup = BeautifulSoup(html, 'html.parser')
    
    if site_name.lower() == "digikala":
        for link in soup.select("a[href*='/product/']"):
            href = link.get("href")
            if href and "/product/" in href:
                if not href.startswith("http"):
                    href = "https://www.digikala.com" + href
                return href
    
    elif site_name.lower() == "snapp shop":
        for link in soup.select("a[href*='/product/'], a[href*='/p/']"):
            href = link.get("href")
            if href and ("/product/" in href or "/p/" in href):
                if not href.startswith("http"):
                    href = "https://snappshop.ir" + href
                return href
    
    elif site_name.lower() == "almas shop":
        for link in soup.select("a[href*='/product/'], .product-item a"):
            href = link.get("href")
            if href:
                if not href.startswith("http"):
                    href = "https://almasshopp.ir" + href
                return href
    
    return None

def fetch_site_data(site_config: dict, phone: str):
    """دریافت اطلاعات از سایت"""
    search_url = site_config["search_url"].replace("{query}", quote_plus(phone))
    
    try:
        response = requests.get(search_url, headers=DEFAULT_HEADERS, timeout=15)
        response.raise_for_status()
        
        # استخراج قیمت
        price = extract_price_from_text(
            response.text,
            site_config.get("price_min", PRICE_MIN_TOMAN),
            site_config.get("price_max", PRICE_MAX_TOMAN)
        )
        
        # استخراج لینک محصول
        product_link = extract_product_link(response.text, site_config["name"]) if price else search_url
        
        return {
            "phone": phone,
            "site": site_config["name"],
            "price": price,
            "link": product_link,
            "status": "found" if price else "not_found",
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
    except Exception as e:
        return {
            "phone": phone,
            "site": site_config["name"],
            "price": None,
            "link": search_url,
            "status": f"error: {str(e)[:50]}",
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

def generate_html(results: list) -> str:
    """تولید فایل HTML نهایی"""
    # مرتب‌سازی نتایج
    sorted_results = sorted(results, key=lambda x: (x["price"] is None, x["price"] if x["price"] else 0))
    
    # ساخت جدول HTML
    rows_html = ""
    for result in sorted_results:
        price_display = f"{result['price']:,}" if result['price'] else "—"
        link_html = f'<a href="{result["link"]}" target="_blank">مشاهده</a>' if result["link"] else "—"
        
        rows_html += f"""
        <tr>
            <td>{result['phone']}</td>
            <td>{price_display}</td>
            <td>{result['site']}</td>
            <td>{link_html}</td>
            <td>{result['checked_at']}</td>
            <td>{result['status']}</td>
        </tr>
        """
    
    html_template = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ردیاب قیمت گوشی</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ 
            max-width: 1200px; 
            margin: 0 auto; 
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{ 
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header p {{ opacity: 0.9; font-size: 1.1em; }}
        .stats {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px; 
            padding: 30px;
            background: #f8f9fa;
        }}
        .stat-card {{ 
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}
        .stat-number {{ font-size: 2em; font-weight: bold; color: #2c3e50; }}
        .stat-label {{ color: #7f8c8d; margin-top: 5px; }}
        table {{ 
            width: 100%; 
            border-collapse: collapse; 
            background: white;
        }}
        th {{ 
            background: #34495e;
            color: white;
            padding: 15px;
            text-align: right;
            font-weight: 600;
        }}
        td {{ 
            padding: 15px;
            text-align: right;
            border-bottom: 1px solid #ecf0f1;
        }}
        tr:hover {{ background: #f8f9fa; }}
        .price {{ font-weight: bold; color: #27ae60; }}
        .no-price {{ color: #e74c3c; }}
        .update-info {{ 
            text-align: center; 
            padding: 20px; 
            background: #ecf0f1;
            color: #7f8c8d;
        }}
        @media (max-width: 768px) {{
            .container {{ margin: 10px; }}
            .header h1 {{ font-size: 1.8em; }}
            table {{ font-size: 0.9em; }}
            th, td {{ padding: 10px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📱 ردیاب قیمت گوشی</h1>
            <p>آخرین آپدیت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{len(results)}</div>
                <div class="stat-label">مجموع بررسی‌ها</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len([r for r in results if r['price']])}</div>
                <div class="stat-label">قیمت‌های پیدا شده</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len(set(r['phone'] for r in results))}</div>
                <div class="stat-label">مدل گوشی</div>
            </div>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>مدل گوشی</th>
                    <th>قیمت (تومان)</th>
                    <th>فروشگاه</th>
                    <th>لینک محصول</th>
                    <th>زمان بررسی</th>
                    <th>وضعیت</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        
        <div class="update-info">
            <p>🔄 هر 10 دقیقه به‌صورت خودکار آپدیت می‌شود</p>
        </div>
    </div>
</body>
</html>"""
    
    return html_template

def main():
    """تابع اصلی"""
    print("Starting phone price tracker...")
    
    # خواندن تنظیمات
    try:
        with open('phones.json', 'r', encoding='utf-8') as f:
            phones = json.load(f)
        
        with open('sites.json', 'r', encoding='utf-8') as f:
            sites = json.load(f)
    except Exception as e:
        print(f"Error reading config files: {e}")
        return
    
    print(f"Found {len(phones)} phones and {len(sites)} sites")
    
    # جمع‌آوری اطلاعات
    results = []
    for i, phone in enumerate(phones, 1):
        print(f"Checking {phone} ({i}/{len(phones)})...")
        
        for site in sites:
            print(f"  {site['name']}...")
            result = fetch_site_data(site, phone)
            results.append(result)
            
            # تأخیر بین درخواست‌ها
            time.sleep(2)
    
    # تولید فایل HTML
    html_content = generate_html(results)
    
    # ذخیره فایل
    output_file = Path('index.html')
    output_file.write_text(html_content, encoding='utf-8')
    
    print(f"Output file created: {output_file}")
    print(f"Found {len([r for r in results if r['price']])} prices")

if __name__ == "__main__":
    main()
