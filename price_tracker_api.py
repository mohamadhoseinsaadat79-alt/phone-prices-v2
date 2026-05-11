#!/usr/bin/env python3
"""
ردیاب قیمت گوشی - نسخه با API و سایت‌های جایگزین
استفاده از API‌های قیمت و سایت‌های خارجی که تحریم نیستن
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

# API‌های قیمت گوشی (تستی)
PRICE_APIS = [
    {
        "name": "PhoneArena API",
        "url": "https://www.phonearena.com/phones/search?q={query}",
        "price_selector": ".price",
        "link_selector": ".phone-item a",
    },
    {
        "name": "GSM Arena",
        "url": "https://www.gsmarena.com/results.php3?sQuickSearch=yes&sName={query}",
        "price_selector": ".price",
        "link_selector": ".maker a",
    }
]

# سایت‌های جایگزین که از ایران قابل دسترسن
ALTERNATIVE_SITES = [
    {
        "name": "TechSpot",
        "url": "https://www.techspot.com/search?q={query}",
        "price_selector": ".price",
        "link_selector": ".result-title a",
    },
    {
        "name": "CNET",
        "url": "https://www.cnet.com/search/?query={query}",
        "price_selector": ".price",
        "link_selector": ".result a",
    }
]

# قیمت‌های شبیه‌سازی شده برای تست (تا API واقعی پیدا بشه)
MOCK_PRICES = {
    "iPhone 13 128GB": {
        "Digikala": 45_000_000,
        "Snapp Shop": 44_500_000,
        "Almas Shop": 46_200_000,
    },
    "Samsung Galaxy A55 256GB": {
        "Digikala": 18_500_000,
        "Snapp Shop": 18_200_000,
        "Almas Shop": 19_100_000,
    },
    "Xiaomi Redmi Note 13 Pro 256GB": {
        "Digikala": 12_800_000,
        "Snapp Shop": 12_500_000,
        "Almas Shop": 13_200_000,
    }
}

def get_mock_price(phone: str, site: str) -> int:
    """دریافت قیمت شبیه‌سازی شده برای تست"""
    return MOCK_PRICES.get(phone, {}).get(site, 0)

def fetch_from_api(phone: str, api_config: dict) -> dict:
    """دریافت قیمت از API"""
    try:
        url = api_config["url"].replace("{query}", quote_plus(phone))
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/html",
        }
        
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        
        # استخراج قیمت از HTML (چون API واقعی نداریم)
        soup = BeautifulSoup(response.text, 'html.parser')
        price_element = soup.select_one(api_config["price_selector"])
        
        if price_element:
            price_text = price_element.get_text()
            price_match = re.search(r'([\d,]+)', price_text)
            if price_match:
                price = int(price_match.group(1).replace(',', ''))
                return {
                    "phone": phone,
                    "site": api_config["name"],
                    "price": price,
                    "status": "found",
                    "source": "api"
                }
        
        return {
            "phone": phone,
            "site": api_config["name"],
            "price": None,
            "status": "not_found",
            "source": "api"
        }
        
    except Exception as e:
        return {
            "phone": phone,
            "site": api_config["name"],
            "price": None,
            "status": f"error: {str(e)[:50]}",
            "source": "api"
        }

def fetch_site_data(site_config: dict, phone: str):
    """دریافت اطلاعات از سایت با روش ترکیبی"""
    checked = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # اول از قیمت شبیه‌سازی شده استفاده می‌کنیم (برای تست)
    mock_price = get_mock_price(phone, site_config["name"])
    if mock_price > 0:
        return {
            "phone": phone,
            "price": mock_price,
            "site_name": site_config["name"],
            "site_url": site_config["search_url"].replace("{query}", quote_plus(phone)),
            "checked_at": checked,
            "status": "found",
            "source": "mock"
        }
    
    # اگر قیمت شبیه‌سازی شده نداشت، سعی می‌کنیم از API بگیریم
    try:
        # برای سایت‌های اصلی، سعی می‌کنیم با هدرهای مختلف درخواست بدیم
        headers_list = [
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
        ]
        
        url = site_config["search_url"].replace("{query}", quote_plus(phone))
        
        for headers in headers_list:
            try:
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code == 200:
                    # استخراج قیمت با الگوهای مختلف
                    price_patterns = [
                        r'"price":\s*(\d+)',
                        r'data-price="(\d+)"',
                        r'price[^>]*>([\d,]+)',
                        r'(\d[\d,]*)\s*تومان',
                        r'(\d[\d,]*)\s*ریال',
                    ]
                    
                    for pattern in price_patterns:
                        matches = re.findall(pattern, response.text)
                        for match in matches:
                            price = int(re.sub(r'[^\d]', '', str(match)))
                            if 100_000 <= price <= 1_000_000_000:  # محدوده معقول قیمت
                                return {
                                    "phone": phone,
                                    "price": price,
                                    "site_name": site_config["name"],
                                    "site_url": url,
                                    "checked_at": checked,
                                    "status": "found",
                                    "source": "scraped"
                                }
                    
                    # اگر قیمت پیدا نشد، ولی صفحه بار شد
                    return {
                        "phone": phone,
                        "price": None,
                        "site_name": site_config["name"],
                        "site_url": url,
                        "checked_at": checked,
                        "status": "not_found",
                        "source": "scraped"
                    }
                    
            except requests.exceptions.RequestException:
                continue
        
        # اگر هیچ‌کدوم از هدرها کار نکرد
        return {
            "phone": phone,
            "price": None,
            "site_name": site_config["name"],
            "site_url": url,
            "checked_at": checked,
            "status": "blocked",
            "source": "scraped"
        }
        
    except Exception as e:
        return {
            "phone": phone,
            "price": None,
            "site_name": site_config["name"],
            "site_url": site_config["search_url"].replace("{query}", quote_plus(phone)),
            "checked_at": checked,
            "status": f"error: {str(e)[:50]}",
            "source": "error"
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
            "blocked": "🚫 مسدود",
            "error": "❌ خطا",
        }
        
        source_map = {
            "mock": "🧪 شبیه‌سازی",
            "scraped": "🌐 استخراج",
            "api": "📡 API",
        }
        
        status_text = status_map.get(result['status'], result['status'])
        source_text = source_map.get(result.get('source', ''), '')
        
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
            <td>{source_text}</td>
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
    <title>ردیاب قیمت گوشی - نسخه API</title>
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
        .source {{ font-size: 0.9em; color: #7f8c8d; }}
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
        .api-info {{
            background: #d1ecf1;
            color: #0c5460;
            padding: 15px;
            margin: 20px;
            border-radius: 8px;
            text-align: center;
            border: 1px solid #bee5eb;
        }}
        .mock-info {{
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
            <h1>📱 ردیاب قیمت گوشی - نسخه API</h1>
            <p>آخرین آپدیت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="mock-info">
            🧪 این نسخه از قیمت‌های شبیه‌سازی شده برای تست استفاده می‌کند. قیمت‌ها واقعی نیستند!
        </div>
        
        <div class="api-info">
            📡 در نسخه نهایی از API‌های واقعی و سایت‌های جایگزین استفاده خواهد شد.
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
                    <th>منبع</th>
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
    print("Starting API phone price tracker...")
    
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
            time.sleep(random.uniform(1, 3))
    
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
            "blocked": "BLOCKED",
            "error": "ERROR",
        }.get(result['status'], "ERROR")
        source_text = result.get('source', 'unknown')
        print(f"{status_text} {result['site_name']}: {result['status']} ({source_text})")

if __name__ == "__main__":
    main()
