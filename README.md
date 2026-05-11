# 📱 ردیاب قیمت گوشی

برنامه‌ای برای ردیاب قیمت گوشی از فروشگاه‌های ایرانی با آپدیت خودکار هر 10 دقیقه.

## 🚀 ویژگی‌ها

- ✅ آپدیت خودکار هر 10 دقیقه
- 🌐 میزبانی رایگان روی GitHub Pages
- 📱 ریسپانسیو و زیبا
- 🔗 لینک مستقیم محصول
- 📊 آمار و نمودار
- ⚡ سریع و پایدار

## 📋 فروشگاه‌ها

- دیجی‌کالا
- اسنپ‌شاپ
- الماس‌شاپ

## 🔧 نصب و اجرا

### ۱. نصب نیازمندی‌ها
```bash
pip install -r requirements.txt
```

### ۲. اجرای برنامه
```bash
python price_tracker.py
```

### ۳. مشاهده خروجی
فایل `index.html` رو در مرورگر باز کن.

## 🌐 انتشار روی GitHub

### ۱. آپلود به GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/username/phone-prices.git
git push -u origin main
```

### ۲. فعال کردن GitHub Pages
1. به ریپازیتوری برید
2. Settings → Pages
3. Source رو روی Deploy from a branch تنظیم کن
4. Branch رو main و Folder رو / (root) انتخاب کن
5. Save رو بزن

### ۳. لینک سایت شما
```
https://username.github.io/phone-prices/
```

## ⚙️ تنظیمات

### افزودن گوشی جدید
فایل `phones.json` رو ویرایش کن:
```json
[
  "iPhone 13 128GB",
  "Samsung Galaxy A55 256GB",
  "Xiaomi Redmi Note 13 Pro 256GB",
  "گوشی جدید"
]
```

### افزودن فروشگاه جدید
فایل `sites.json` رو ویرایش کن:
```json
[
  {
    "name": "نام فروشگاه",
    "search_url": "https://example.com/search?q={query}",
    "price_min": 1000000,
    "price_max": 200000000
  }
]
```

## 🔄 آپدیت خودکار

برنامه هر 10 دقیقه به صورت خودکار توسط GitHub Actions اجرا می‌شه و سایت آپدیت می‌شه.

## 📊 آمار

- تعداد کل بررسی‌ها
- قیمت‌های پیدا شده
- مدل‌های گوشی

## 🎯 نتیجه نهایی

سایت شما روی آدرس زیر در دسترس خواهد بود:
```
https://mohamadhoseinsaadat79-alt.github.io/phone-prices/
```

این لینک رو به دوستانتون بدید تا قیمت‌ها رو ببینن!
