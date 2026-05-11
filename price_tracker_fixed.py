#!/usr/bin/env python3
"""
ردیاب قیمت گوشی - نسخه اصلاح شده
خروجی مستقیم HTML برای GitHub Pages با فرم افزودن گوشی
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

# تنظیمات بهبود یافته
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Cache-Control": "max-age=0"
}

PRICE_MIN_TOMAN = 500_000
PRICE_MAX_TOMAN = 200_000_000
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
    """دریافت اطلاعات از سایت با روش بهبود یافته"""
    search_url = site_config["search_url"].replace("{query}", quote_plus(phone))
    
    try:
        # استفاده از session برای بهتر شدن درخواست
        session = requests.Session()
        session.headers.update(DEFAULT_HEADERS)
        
        # اضافه کردن random delay برای جلوگیری از بلاک
        time.sleep(random.uniform(1, 3))
        
        response = session.get(search_url, timeout=20)
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
        
    except requests.exceptions.RequestException as e:
        return {
            "phone": phone,
            "site": site_config["name"],
            "price": None,
            "link": search_url,
            "status": f"connection_error",
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        return {
            "phone": phone,
            "site": site_config["name"],
            "price": None,
            "link": search_url,
            "status": f"general_error",
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

def add_new_phone(phone_name: str):
    """افزودن گوشی جدید به لیست"""
    try:
        with open('phones.json', 'r', encoding='utf-8') as f:
            phones = json.load(f)
        
        if phone_name not in phones:
            phones.append(phone_name)
            
            with open('phones.json', 'w', encoding='utf-8') as f:
                json.dump(phones, f, ensure_ascii=False, indent=2)
            
            return True
        return False
    except Exception:
        return False

def generate_html(results: list, current_phones: list) -> str:
    """تولید فایل HTML نهایی با فرم افزودن گوشی"""
    # مرتب‌سازی نتایج
    sorted_results = sorted(results, key=lambda x: (x["price"] is None, x["price"] if x["price"] else 0))
    
    # ساخت جدول HTML
    rows_html = ""
    for result in sorted_results:
        price_display = f"{result['price']:,}" if result['price'] else "—"
        link_html = f'<a href="{result["link"]}" target="_blank">مشاهده</a>' if result["link"] else "—"
        
        status_text = "پیدا شد" if result['status'] == 'found' else "پیدا نشد" if result['status'] == 'not_found' else "خطا"
        status_class = "success" if result['status'] == 'found' else "warning" if result['status'] == 'not_found' else "error"
        
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
        .price {{ font-weight: bold; color: #27ae60; }}
        .no-price {{ color: #e74c3c; }}
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
            <h1>📱 ردیاب قیمت گوشی</h1>
            <p>آخرین آپدیت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
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
    print("Starting phone price tracker...")
    
    # خواندن تنظیمات
    try:
        with open('phones.json', 'r', encoding='utf-8') as f:
            phones = json.load(f)
        
        # خواندن گوشی‌های جدید از localStorage (در محیط GitHub این کار نمی‌کنه)
        # در نسخه وب این کار با JavaScript انجام می‌شه
        
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
            
            # تأخیر بیشتر بین درخواست‌ها
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
