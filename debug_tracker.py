#!/usr/bin/env python3
"""
دیباگ کردن ردیاب قیمت - پیدا کردن مشکل اصلی
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

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
}

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

def debug_site(site_config: dict, phone: str):
    """دیباگ کردن یک سایت"""
    print(f"\n=== DEBUG: {site_config['name']} - {phone} ===")
    
    url = site_config["search_url"].replace("{query}", quote_plus(phone))
    print(f"URL: {url}")
    
    try:
        # درخواست ساده
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=20)
        print(f"Status Code: {response.status_code}")
        print(f"Content Length: {len(response.text)}")
        
        if response.status_code != 200:
            print(f"ERROR: HTTP {response.status_code}")
            return None, None, f"HTTP {response.status_code}"
        
        # نمایش چند خط اول HTML
        print("First 500 chars of HTML:")
        print(response.text[:500])
        print("...")
        
        # استخراج قیمت
        price = None
        if site_config.get("parse") == "almas_cards":
            lo = site_config.get("price_min", PRICE_MIN_TOMAN)
            hi = site_config.get("price_max", PRICE_MAX_TOMAN)
            soup = BeautifulSoup(response.text, "lxml")
            
            # دیباگ الماس‌شاپ
            print("Looking for .products-item-price...")
            price_elements = soup.select(".products-item-price")
            print(f"Found {len(price_elements)} price elements")
            
            for i, el in enumerate(price_elements):
                chunk = el.get_text(" ", strip=True)
                print(f"Price element {i}: '{chunk}'")
                v = first_price_in_range(chunk, lo, hi)
                if v is not None:
                    print(f"Found price: {v}")
                    price = v
                    break
        else:
            # دیباگ سایت‌های دیگر
            text = response.text
            price = smart_product_price(
                text,
                prefer_min=site_config.get("price_min"),
                prefer_max=site_config.get("price_max"),
                strict_range=True
            )
            print(f"Smart price result: {price}")
        
        # استخراج لینک
        soup = BeautifulSoup(response.text, 'html.parser')
        product_link = None
        
        if site_config["name"].lower() == "digikala":
            links = soup.select("a[href*='/product/']")
            print(f"Found {len(links)} Digikala product links")
            for link in links[:3]:  # فقط 3 تا اول
                href = link.get("href")
                if href and "/product/" in href:
                    if not href.startswith("http"):
                        href = "https://www.digikala.com" + href
                    product_link = href
                    print(f"Product link: {href}")
                    break
        
        elif site_config["name"].lower() == "snapp shop":
            links = soup.select("a[href*='/product/'], a[href*='/p/']")
            print(f"Found {len(links)} Snapp Shop links")
            for link in links[:3]:
                href = link.get("href")
                if href and ("/product/" in href or "/p/" in href):
                    if not href.startswith("http"):
                        href = "https://snappshop.ir" + href
                    product_link = href
                    print(f"Product link: {href}")
                    break
        
        elif site_config["name"].lower() == "almas shop":
            links = soup.select("a[href*='/product/'], .product-item a")
            print(f"Found {len(links)} Almas Shop links")
            for link in links[:3]:
                href = link.get("href")
                if href:
                    if not href.startswith("http"):
                        href = "https://almasshopp.ir" + href
                    product_link = href
                    print(f"Product link: {href}")
                    break
        
        return price, product_link, "ok"
        
    except Exception as e:
        print(f"ERROR: {e}")
        return None, None, f"error: {str(e)}"

def main():
    """تابع اصلی دیباگ"""
    print("Starting DEBUG tracker...")
    
    try:
        with open('phones.json', 'r', encoding='utf-8') as f:
            phones = json.load(f)
        
        with open('sites.json', 'r', encoding='utf-8') as f:
            sites = json.load(f)
    except Exception as e:
        print(f"Error reading config files: {e}")
        return
    
    # فقط اولین گوشی رو دیباگ می‌کنیم
    phone = phones[0]
    print(f"Debugging phone: {phone}")
    
    for site in sites:
        price, link, status = debug_site(site, phone)
        print(f"\nRESULT: price={price}, link={link}, status={status}")
        print("=" * 50)
        time.sleep(2)

if __name__ == "__main__":
    main()
