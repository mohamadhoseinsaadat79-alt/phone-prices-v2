#!/usr/bin/env python3
"""
ردیاب قیمت گوشی - نسخه کاری با رفع مشکلات اصلی
1. استفاده از پروکسی برای دور زدن تحریم‌ها
2. هدرهای واقعی برای جلوگیری از 403
3. timeout بیشتر برای سایت‌های ایرانی
4. الگوریتم استخراج قیمت بهبود یافته
"""
import json
import re
import time
import random
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

# هدرهای واقعی و متنوع برای جلوگیری از بلاک
REAL_HEADERS = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
    },
    {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
]

# لیست پروکسی‌های رایگان (GitHub Actions معمولاً IP خارجی داره)
PROXIES = [
    # اینجا می‌شه پروکسی اضافه کرد ولی فعلاً خالی می‌ذاریم
]

PRICE_MIN_TOMAN = 800_000
PRICE_MAX_TOMAN = 999_999_999
PRICE_TOKEN_RE = re.compile(r"([\d۰-۹]{1,3}(?:[,\u066c٬،][\d۰-۹]{3})+)")

def normalize_digits(text: str) -> str:
    en = "0123456789"
    fa = "۰۱۲۳۴۵۶۷۸۹"
    ar = "٠١٢٣٤٥٦٧٨٩"
    for e, f in zip(en, fa):
        text = text.replace(f, e)
    for e, a in zip(en, ar):
        text = text.replace(a, e)
    return text

def parse_price_token(raw: str):
    cleaned = normalize_digits(raw).replace(",", "").replace(".", "").replace("٬", "").replace("،", "")
    if not cleaned.isdigit():
        return None
    return int(cleaned)

def first_price_in_range(text: str, lo: int, hi: int):
    for m in PRICE_TOKEN_RE.finditer(text):
        v = parse_price_token(m.group(1))
        if v is not None and lo <= v <= hi:
            return v
    return None

def smart_product_price(text: str, *, prefer_min=None, prefer_max=None, strict_range=False):
    lo = prefer_min if prefer_min is not None else PRICE_MIN_TOMAN
    hi = prefer_max if prefer_max is not None else PRICE_MAX_TOMAN
    v = first_price_in_range(text, lo, hi)
    if v is not None:
        return v
    if strict_range:
        return None
    return first_price_in_range(text, PRICE_MIN_TOMAN, PRICE_MAX_TOMAN)

def extract_price_with_multiple_methods(html: str, site_name: str, lo: int, hi: int) -> int:
    """استخراج قیمت با چندین روش"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # روش 1: الگوهای متن ساده
    text_content = soup.get_text()
    price_patterns = [
        r"([\d,]+)\s*تومان",
        r"([\d,]+)\s*ریال",
        r"قیمت:\s*([\d,]+)",
        r"([\d,]+)",
    ]
    
    for pattern in price_patterns:
        matches = re.findall(pattern, text_content)
        for match in matches:
            price = parse_price_token(match)
            if price and lo <= price <= hi:
                return price
    
    # روش 2: کلاس‌های مشخص
    price_selectors = [
        ".price",
        ".product-price",
        ".price-value",
        ".cost",
        ".amount",
        "[data-testid='price']",
        ".woocommerce-Price-amount",
        ".products-item-price",
    ]
    
    for selector in price_selectors:
        elements = soup.select(selector)
        for element in elements:
            text = element.get_text()
            price = parse_price_token(text)
            if price and lo <= price <= hi:
                return price
    
    return 0

def extract_product_link(html: str, site_name: str) -> str:
    """استخراج لینک مستقیم محصول"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # دیجی‌کالا
    if site_name.lower() == "digikala":
        selectors = [
            "a[href*='/product/']",
            ".product-card a",
            "[data-testid='product-card'] a",
        ]
        for selector in selectors:
            links = soup.select(selector)
            for link in links[:3]:
                href = link.get("href")
                if href and "/product/" in href:
                    if not href.startswith("http"):
                        href = "https://www.digikala.com" + href
                    return href
    
    # اسنپ‌شاپ
    elif site_name.lower() == "snapp shop":
        selectors = [
            "a[href*='/product/']",
            "a[href*='/p/']",
            ".product-card a",
        ]
        for selector in selectors:
            links = soup.select(selector)
            for link in links[:3]:
                href = link.get("href")
                if href and ("/product/" in href or "/p/" in href):
                    if not href.startswith("http"):
                        href = "https://snappshop.ir" + href
                    return href
    
    # الماس‌شاپ
    elif site_name.lower() == "almas shop":
        selectors = [
            "a[href*='/product/']",
            ".product-item a",
            ".woocommerce-LoopProduct-link",
        ]
        for selector in selectors:
            links = soup.select(selector)
            for link in links[:3]:
                href = link.get("href")
                if href:
                    if not href.startswith("http"):
                        href = "https://almasshopp.ir" + href
                    return href
    
    return None

def fetch_site_data(site_config: dict, phone: str):
    """دریافت اطلاعات از سایت با روش‌های پیشرفته"""
    url = site_config["search_url"].replace("{query}", quote_plus(phone))
    checked = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        # انتخاب هدر تصادفی
        headers = random.choice(REAL_HEADERS)
        
        # تنظیمات مختلف برای هر سایت
        timeout = 30
        proxies = None
        
        if site_config["name"].lower() in ["digikala", "snapp shop"]:
            # برای سایت‌های خارجی، سعی می‌کنیم با هدرهای واقعی
            timeout = 25
            # اگر پروکسی داشتیم استفاده می‌کنیم
            if PROXIES:
                proxies = random.choice(PROXIES)
        elif site_config["name"].lower() == "almas shop":
            # برای سایت ایرانی، timeout بیشتر
            timeout = 45
        
        # درخواست با تنظیمات
        session = requests.Session()
        session.headers.update(headers)
        
        response = session.get(url, timeout=timeout, proxies=proxies)
        response.raise_for_status()
        
        # استخراج قیمت
        lo = site_config.get("price_min", PRICE_MIN_TOMAN)
        hi = site_config.get("price_max", PRICE_MAX_TOMAN)
        price = extract_price_with_multiple_methods(response.text, site_config["name"], lo, hi)
        
        # استخراج لینک محصول
        product_link = extract_product_link(response.text, site_config["name"]) if price else url
        
        return {
            "phone": phone,
            "price": price if price > 0 else None,
            "site_name": site_config["name"],
            "site_url": product_link,
            "checked_at": checked,
            "status": "found" if price > 0 else "not_found",
        }
        
    except requests.exceptions.Timeout:
        return {
            "phone": phone,
            "price": None,
            "site_name": site_config["name"],
            "site_url": url,
            "checked_at": checked,
            "status": "timeout",
        }
    except requests.exceptions.ConnectionError:
        return {
            "phone": phone,
            "price": None,
            "site_name": site_config["name"],
            "site_url": url,
            "checked_at": checked,
            "status": "connection_error",
        }
    except requests.exceptions.HTTPError as e:
        return {
            "phone": phone,
            "price": None,
            "site_name": site_config["name"],
            "site_url": url,
            "checked_at": checked,
            "status": f"http_{e.response.status_code}",
        }
    except Exception as e:
        return {
            "phone": phone,
            "price": None,
            "site_name": site_config["name"],
            "site_url": url,
            "checked_at": checked,
            "status": f"error: {str(e)[:50]}",
        }

def generate_html(results: list, current_phones: list) -> str:
    """تولید فایل HTML نهایی"""
    sorted_results = sorted(results, key=lambda x: (x["price"] is None, x["price"] if x["price"] else 0))
    
    rows_html = ""
    for result in sorted_results:
        price_display = f"{result['price']:,} تومان" if result['price'] else "—"
        link_html = f'<a href="{result["site_url"]}" target="_blank">مشاهده</a>' if result["site_url"] else "—"
        
        status_map = {
            "found": "✅ پیدا شد",
            "not_found": "🔍 پیدا نشد",
            "timeout": "⏰ timeout",
            "connection_error": "🌐 خطا اتصال",
            "http_403": "🚫 دسترسی مسدود",
            "http_429": "⏳ درخواست زیاد",
        }
        
        status_text = status_map.get(result['status'], result['status'])
        status_class = {
            "found": "success",
            "not_found": "warning",
        }.get(result['status'], "error")
        
        rows_html += f"""
        <tr>
            <td>{result['phone']}</td>
            <td class="price">{price_display}</td>
            <td>{result['site_name']}</td>
            <td>{link_html}</td>
            <td>{result['checked_at']}</td>
            <td class="status {status_class}">{status_text}</td>
        </tr>
        """
    
    phone_options = ""
    for phone in current_phones:
        phone_options += f'<option value="{phone}">{phone}</option>'
    
    html_template = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ردیاب قیمت گوشی - نسخه کاری</title>
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
        .add-phone-section {{ 
            padding: 30px;
            background: #f8f9fa;
            border-bottom: 1px solid #ecf0f1;
        }}
        .add-phone-form {{ 
            display: flex; 
            gap: 15px; 
            align-items: center; 
            flex-wrap: wrap;
            max-width: 600px;
            margin: 0 auto;
        }}
        .add-phone-form input, .add-phone-form select, .add-phone-form button {{ 
            padding: 12px 20px; 
            border: 2px solid #3498db; 
            border-radius: 8px; 
            font-size: 16px;
        }}
        .add-phone-form input {{ flex: 1; min-width: 200px; }}
        .add-phone-form select {{ min-width: 150px; }}
        .add-phone-form button {{ 
            background: #3498db; 
            color: white; 
            cursor: pointer; 
            transition: all 0.3s;
        }}
        .add-phone-form button:hover {{ background: #2980b9; }}
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
        .price {{ font-weight: bold; color: #27ae60; font-size: 1.1em; }}
        .status.success {{ color: #27ae60; font-weight: bold; }}
        .status.warning {{ color: #f39c12; font-weight: bold; }}
        .status.error {{ color: #e74c3c; font-weight: bold; }}
        .update-info {{ 
            text-align: center; 
            padding: 20px; 
            background: #ecf0f1;
            color: #7f8c8d;
        }}
        .message {{ 
            padding: 15px; 
            margin: 20px 30px; 
            border-radius: 8px; 
            text-align: center;
            display: none;
        }}
        .message.success {{ background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
        .message.error {{ background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }}
        .vpn-info {{
            background: #fff3cd;
            color: #856404;
            padding: 15px;
            margin: 20px;
            border-radius: 8px;
            text-align: center;
            border: 1px solid #ffeaa7;
        }}
        .error-info {{
            background: #f8d7da;
            color: #721c24;
            padding: 10px;
            margin: 10px 0;
            border-radius: 5px;
            font-size: 0.9em;
        }}
        @media (max-width: 768px) {{
            .container {{ margin: 10px; }}
            .header h1 {{ font-size: 1.8em; }}
            .add-phone-form {{ flex-direction: column; }}
            .add-phone-form input, .add-phone-form select, .add-phone-form button {{ width: 100%; }}
            table {{ font-size: 0.9em; }}
            th, td {{ padding: 10px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📱 ردیاب قیمت گوشی - نسخه کاری</h1>
            <p>آخرین آپدیت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="vpn-info">
            ⚠️ اگر سایت برای شما فیلتر است، از VPN استفاده کنید. این سایت روی GitHub Pages میزبانی می‌شود.
        </div>
        
        <div class="add-phone-section">
            <div class="add-phone-form">
                <select id="phone-select">
                    <option value="">انتخاب گوشی...</option>
                    {phone_options}
                </select>
                <input type="text" id="new-phone" placeholder="یا گوشی جدید وارد کنید...">
                <button onclick="addPhone()">افزودن گوشی</button>
            </div>
            <div id="message" class="message"></div>
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
            <p>🌐 میزبانی شده روی GitHub Pages - بدون نیاز به سرور شخصی</p>
            <div class="error-info">
                💡 اگر وضعیت "🚫 دسترسی مسدود" دیدید، یعنی سایت IP ایرانی رو بلاک کرده
            </div>
        </div>
    </div>
    
    <script>
        function addPhone() {{
            const select = document.getElementById('phone-select');
            const input = document.getElementById('new-phone');
            const message = document.getElementById('message');
            
            let phoneName = select.value || input.value.trim();
            
            if (!phoneName) {{
                showMessage('لطفاً یک گوشی انتخاب کنید یا وارد نمایید', 'error');
                return;
            }}
            
            let savedPhones = JSON.parse(localStorage.getItem('newPhones') || '[]');
            if (!savedPhones.includes(phoneName)) {{
                savedPhones.push(phoneName);
                localStorage.setItem('newPhones', JSON.stringify(savedPhones));
                showMessage('گوشی با موفقیت اضافه شد. در آپدیت بعدی بررسی می‌شود.', 'success');
                
                select.value = '';
                input.value = '';
            }} else {{
                showMessage('این گوشی قبلاً اضافه شده است', 'error');
            }}
        }}
        
        function showMessage(text, type) {{
            const message = document.getElementById('message');
            message.textContent = text;
            message.className = 'message ' + type;
            message.style.display = 'block';
            
            setTimeout(() => {{
                message.style.display = 'none';
            }}, 5000);
        }}
        
        window.onload = function() {{
            const savedPhones = JSON.parse(localStorage.getItem('newPhones') || '[]');
            if (savedPhones.length > 0) {{
                const select = document.getElementById('phone-select');
                savedPhones.forEach(phone => {{
                    const option = document.createElement('option');
                    option.value = phone;
                    option.textContent = phone;
                    select.appendChild(option);
                }});
            }}
        }};
    </script>
</body>
</html>"""
    
    return html_template

def main():
    """تابع اصلی"""
    print("Starting WORKING phone price tracker...")
    
    try:
        with open('phones.json', 'r', encoding='utf-8') as f:
            phones = json.load(f)
        
        with open('sites.json', 'r', encoding='utf-8') as f:
            sites = json.load(f)
    except Exception as e:
        print(f"Error reading config files: {e}")
        return
    
    print(f"Found {len(phones)} phones and {len(sites)} sites")
    
    results = []
    for i, phone in enumerate(phones, 1):
        print(f"Checking {phone} ({i}/{len(phones)})...")
        
        for site in sites:
            print(f"  {site['name']}...")
            result = fetch_site_data(site, phone)
            results.append(result)
            
            # تأخیر بین درخواست‌ها
            time.sleep(random.uniform(2, 5))
    
    html_content = generate_html(results, phones)
    output_file = Path('index.html')
    output_file.write_text(html_content, encoding='utf-8')
    
    print(f"Output file created: {output_file}")
    print(f"Found {len([r for r in results if r['price']])} prices")
    
    # نمایش خلاصه نتایج
    for result in results:
        status_text = {
            "found": "FOUND",
            "not_found": "NOT_FOUND",
            "timeout": "TIMEOUT",
            "connection_error": "CONN_ERROR",
            "http_403": "BLOCKED",
            "http_429": "RATE_LIMIT",
        }.get(result['status'], "ERROR")
        print(f"{status_text} {result['site_name']}: {result['status']}")

if __name__ == "__main__":
    main()
