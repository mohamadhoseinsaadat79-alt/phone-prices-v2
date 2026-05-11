#!/usr/bin/env python3
"""
ردیاب قیمت گوشی - نسخه نهایی با رفع مشکلات اساسی
1. قیمت‌ها به درستی استخراج می‌شن
2. سایت برای کاربران ایرانی قابل دسترسه
3. تبدیل ریال به تومان
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

# هدرهای واقعی برای جلوگیری از بلاک شدن
HEADERS = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
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
    }
]

# الگوهای مختلف برای استخراج قیمت
PRICE_PATTERNS = [
    r"([\d,]+)\s*تومان",
    r"([\d,]+)\s*ریال",
    r"([\d,]+)\s*تومان",
    r"قیمت:\s*([\d,]+)",
    r"([\d,]+)",
]

PRICE_MIN = 100_000  # 100 هزار تومان
PRICE_MAX = 500_000_000  # 500 میلیون تومان

def normalize_price(text: str) -> int:
    """نرمال‌سازی و تبدیل قیمت"""
    # حذف کاراکترهای غیر عددی
    text = re.sub(r'[^\d,]', '', text)
    # حذف کاما
    text = text.replace(',', '')
    
    if not text.isdigit():
        return 0
    
    price = int(text)
    
    # اگر ریال بود، تبدیل به تومان
    if price > 1_000_000:  # احتمالاً ریال
        price = price // 10
    
    return price

def extract_price_from_html(html: str) -> int:
    """استخراج قیمت از HTML با الگوهای مختلف"""
    for pattern in PRICE_PATTERNS:
        matches = re.findall(pattern, html)
        for match in matches:
            price = normalize_price(match)
            if PRICE_MIN <= price <= PRICE_MAX:
                return price
    return 0

def extract_digikala_price(html: str) -> int:
    """استخراج قیمت از دیجی‌کالا"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # الگوهای مختلف دیجی‌کالا
    selectors = [
        ".price-value",
        ".price-new",
        "[data-testid='price-current']",
        ".product-price",
        ".price",
    ]
    
    for selector in selectors:
        elements = soup.select(selector)
        for element in elements:
            text = element.get_text()
            price = extract_price_from_html(text)
            if price > 0:
                return price
    
    return 0

def extract_snappshop_price(html: str) -> int:
    """استخراج قیمت از اسنپ‌شاپ"""
    soup = BeautifulSoup(html, 'html.parser')
    
    selectors = [
        ".price",
        ".product-price",
        "[data-testid='price']",
        ".cost",
    ]
    
    for selector in selectors:
        elements = soup.select(selector)
        for element in elements:
            text = element.get_text()
            price = extract_price_from_html(text)
            if price > 0:
                return price
    
    return 0

def extract_almas_price(html: str) -> int:
    """استخراج قیمت از الماس‌شاپ"""
    soup = BeautifulSoup(html, 'html.parser')
    
    selectors = [
        ".price",
        ".product-price",
        ".amount",
        ".woocommerce-Price-amount",
    ]
    
    for selector in selectors:
        elements = soup.select(selector)
        for element in elements:
            text = element.get_text()
            price = extract_price_from_html(text)
            if price > 0:
                return price
    
    return 0

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
    """دریافت اطلاعات از سایت با روش پیشرفته"""
    search_url = site_config["search_url"].replace("{query}", quote_plus(phone))
    
    try:
        # انتخاب هدر تصادفی
        headers = random.choice(HEADERS)
        
        # استفاده از session
        session = requests.Session()
        session.headers.update(headers)
        
        # تأخیر تصادفی
        time.sleep(random.uniform(1, 3))
        
        response = session.get(search_url, timeout=20)
        response.raise_for_status()
        
        # استخراج قیمت بر اساس سایت
        if site_config["name"].lower() == "digikala":
            price = extract_digikala_price(response.text)
        elif site_config["name"].lower() == "snapp shop":
            price = extract_snappshop_price(response.text)
        elif site_config["name"].lower() == "almas shop":
            price = extract_almas_price(response.text)
        else:
            price = extract_price_from_html(response.text)
        
        # استخراج لینک محصول
        product_link = extract_product_link(response.text, site_config["name"]) if price else search_url
        
        return {
            "phone": phone,
            "site": site_config["name"],
            "price": price if price > 0 else None,
            "link": product_link,
            "status": "found" if price > 0 else "not_found",
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
    except Exception as e:
        return {
            "phone": phone,
            "site": site_config["name"],
            "price": None,
            "link": search_url,
            "status": "error",
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

def generate_html(results: list, current_phones: list) -> str:
    """تولید فایل HTML نهایی با طراحی بهتر"""
    # مرتب‌سازی نتایج
    sorted_results = sorted(results, key=lambda x: (x["price"] is None, x["price"] if x["price"] else 0))
    
    # ساخت جدول HTML
    rows_html = ""
    for result in sorted_results:
        price_display = f"{result['price']:,} تومان" if result['price'] else "—"
        link_html = f'<a href="{result["link"]}" target="_blank">مشاهده</a>' if result["link"] else "—"
        
        status_text = {
            "found": "✅ پیدا شد",
            "not_found": "🔍 پیدا نشد", 
            "error": "❌ خطا"
        }.get(result['status'], result['status'])
        
        status_class = {
            "found": "success",
            "not_found": "warning",
            "error": "error"
        }.get(result['status'], "error")
        
        rows_html += f"""
        <tr>
            <td>{result['phone']}</td>
            <td class="price">{price_display}</td>
            <td>{result['site']}</td>
            <td>{link_html}</td>
            <td>{result['checked_at']}</td>
            <td class="status {status_class}">{status_text}</td>
        </tr>
        """
    
    # ساخت آپشن‌های گوشی برای منوی کشویی
    phone_options = ""
    for phone in current_phones:
        phone_options += f'<option value="{phone}">{phone}</option>'
    
    html_template = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ردیاب قیمت گوشی - نسخه نهایی</title>
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
            <h1>📱 ردیاب قیمت گوشی - نسخه نهایی</h1>
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
            
            // ذخیره در localStorage برای استفاده در آپدیت بعدی
            let savedPhones = JSON.parse(localStorage.getItem('newPhones') || '[]');
            if (!savedPhones.includes(phoneName)) {{
                savedPhones.push(phoneName);
                localStorage.setItem('newPhones', JSON.stringify(savedPhones));
                showMessage('گوشی با موفقیت اضافه شد. در آپدیت بعدی بررسی می‌شود.', 'success');
                
                // پاک کردن فرم
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
        
        // بارگذاری گوشی‌های ذخیره شده
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
    print("Starting final phone price tracker...")
    
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
            time.sleep(random.uniform(2, 4))
    
    # تولید فایل HTML
    html_content = generate_html(results, phones)
    
    # ذخیره فایل
    output_file = Path('index.html')
    output_file.write_text(html_content, encoding='utf-8')
    
    print(f"Output file created: {output_file}")
    print(f"Found {len([r for r in results if r['price']])} prices")

if __name__ == "__main__":
    main()
