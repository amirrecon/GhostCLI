![Uploading image.png…]()


# 👻 GhostCLI  

**GhostCLI** یه ابزار خط فرمان (CLI) با حس‌و‌حال هکریه که بهت اجازه میده با مدل‌های OpenRouter (مثل GPT-4o) توی ترمینال چت کنی.  
ویژگی‌هاش شامل مدیریت پرامپت، ذخیره API Key، نگهداری تاریخچه توی دیتابیس SQLite و برندینگ شخصی‌سازی شده‌ست.  

---

## ✨ فیچرها
- 🔑 **مدیریت کلید API**
  - ذخیره و بازیابی API Key از `.env`
  - دستور `/savekeyenv` برای ذخیره کلید

- 🧠 **پرامپت‌ها**
  - `/sys` برای تغییر system prompt  
  - `/persona` برای اضافه کردن پرامپت شخصیت/دید  
  - `/pre` برای اضافه کردن prefix به همه پیام‌ها  

- 💾 **دیتابیس SQLite**
  - ذخیره کامل تاریخچه گفتگوها
  - مدیریت سشن‌ها: `/session new`, `/sessions`, `/use <id>`, `/history`

- 🎨 **برندینگ هکری**
  - واترمارک قابل شخصی‌سازی (`/brand`, `/brandtext`)
  - حالت‌ها: `off`, `left`, `right`, `random`, `floating`

- ⚡ **دیگر امکانات**
  - تغییر مدل با `/model`
  - تغییر Base URL
  - هندلینگ خطا و retry  

---

## 🚀 نصب و اجرا  

### 1. کلون کردن ریپو
```bash
git clone https://github.com/amirrecon/GhostCLI.git
cd GhostCLI
````

### 2. نصب وابستگی‌ها

```bash
pip install -r requirements.txt
```

### 3. ست کردن API Key

روش پیشنهادی: ساخت `.env`

```bash
echo "OPENROUTER_API_KEY=sk-xxxx" > .env
```

یا داخل برنامه دستور `/savekeyenv` رو بزن.

### 4. اجرا

```bash
python -m ghostcli.cli
```

---

## 🖥️ دستورات اصلی

| دستور          | توضیح                     |
| -------------- | ------------------------- |
| `/help`        | نمایش راهنما              |
| `/clear`       | پاک کردن تاریخچه فعلی     |
| `/sys <text>`  | تغییر system prompt       |
| `/persona <p>` | اضافه کردن persona prompt |
| `/pre <text>`  | اضافه کردن prefix         |
| `/model <m>`   | تغییر مدل                 |
| `/savekeyenv`  | ذخیره API Key در `.env`   |
| `/session new` | ساخت سشن جدید             |
| `/sessions`    | لیست سشن‌ها               |
| `/use <id>`    | رفتن به سشن قبلی          |
| `/history`     | دیدن تاریخچه              |
| `/quit`        | خروج                      |

---

## 📂 ساختار پروژه

```
GhostCLI/
├─ src/
│  └─ ghostcli/
│     ├─ __init__.py
│     └─ cli.py
├─ requirements.txt
└─ README.md
```

---

## 📜 مثال استفاده

```text
$ python -m ghostcli.cli
   ____ _               _    ____ _     ___ 
  / ___| |__   ___  ___| | _|  _ \ |   |_ _|
 | |  _| '_ \ / _ \/ __| |/ / | | | |    | | 
 | |_| | | | |  __/ (__|   <| |_| | |___ | | 
  \____|_| |_|\___|\___|_|\_\____/|_____|___|
        👻 GhostCLI — Hacker Vibes Terminal

You: /persona تو یه هکر سایبری هستی با لحن خفن جواب بده  
[✓] Persona prompt set & history reset.  

You: سلام  
GhostCLI:  
هی، خوش اومدی به تاریکی 👻  
```

---

## ⚠️ نکات امنیتی

* API Key رو فقط تو `.env` ذخیره کن.
* دیتابیس (`ghostcli.db`) محتوای چت رو نگه می‌داره → در صورت حساسیت، رمزنگاری یا بکاپ بگیر.

---

## 📌 آینده

* [ ] خروجی گرفتن سشن‌ها به Markdown/JSON
* [ ] استریم توکن‌ها در لحظه
* [ ] پشتیبانی از پلاگین‌ها

---

## 👤 توسعه دهنده 

ساخته شده با 💻 توسط **AmirRecon**
[GitHub](https://github.com/amirrecon)



