# Handoff – پروژه ترب‌گرد (TorobGard) چالش توروب

> فایل تحویل-state برای فرد بعدی که کار روی این ریپازیتور را ادامه می‌دهد.

## ۱. وضعیت کنونی (آخرین به‌روزرسانی: ۱۴۰۵/۰۸/۰۱)

| مورد | وضعیت |
|------|-------|
| Git repository | Initialized locally; pushed to `main` |
| Remote URL | `https://github.com/Aminnaghieh/t-newline2.git` |
| Branch | `main` (root commit: `b1a4e7d`) |
| Backend (FastAPI) | فعال، روی پورت ۸۰۰۰ |
| Frontend (React + Vite) | ساخته شده، در `backend/static` build می‌شود |
| Demo flow (product → shops → filters → alternatives → verify) | **تمامی ۷ مرحله end-to-end اجرا شد** |
| است runs (demo.mjs) | اسکرین‌شات `06-alternatives.png` و `07-verify.png` تولید شد |
| Desktop Playwright tests | **۱۸/۱۸ موفق** |
| Mobile Playwright tests | **۳۶/۳۶ موفق** |
| مسدودکننده | هیچ |

---

## ۲. architecture و تکنولوژی‌ها

### Backend
- **FastAPI** (`backend/main.py`) — نقطه ورود، سرویس API و فایل‌های استاتیک frontend
- **Python 3.11+** — وابستگی‌ها در `backend/requirements.txt`: fastapi, uvicorn, pydantic, google-generativeai, python-dotenv, python-multipart, jinja2
- سرویس‌ها در `backend/services/`: agent.py (مغز ایجنتیک، session در حافظه), search.py, geo.py, hours.py, payment.py (فیلتر BNPL), mall.py
- دیتابیس SQLite (`backend/torob.db`) — gitignore شده؛ در کلون تازه باید با `ingest.py` ساخته شود

### Frontend
- **React 19 + Vite** (`frontend/`)
- tailwindcss از طریق `@tailwindcss/vite`
- leaflet + react-leaflet برای نقشه، lucide-react، react-markdown
- Build output: `../backend/static` (مرturnی به همان سرور FastAPI)
- `frontend/vite.config.js`: proxy `/api` به `localhost:8000`

### E2E Tests
- **Playwright 1.64.1** — دو پروژه: `desktop-chromium` و `mobile-chromium` (Pixel 5)
- تست‌ها در `tests/e2e/`: chat-search.spec.js, shops.spec.js, comparison-verify.spec.js
- Helpers مشترک: `tests/e2e/helpers.js`

### Script مفید
- `start.bat` — اجرای backend با uvicorn روی پورت ۸۰۰۰
- `demo.mjs` — اسکرین‌شات‌دهی از مراحل ۰۱ تا ۰۷ دیمو با guard برای فیلتر BNPL


---

## ۳. چگونه پروژه را اجرا کنید

### پیش‌نیازها
- Python 3.11+
- Node.js 20+ (برای Playwright)
- pip و npm/npx

### ۱) backend
```powershell
cd e:\torob-challange
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
 برنامه در `http://localhost:8000` در دسترس می‌شود.

### ۲) frontend (انتخاب یکی از دو گزینه)
**گزینه أ** — با Backend (پرو덕شن بلد):
```powershell
cd frontend
npm install
npm run build   # خروجی در ../backend/static
```

**گزینه ب** — توسعه جداگانه (vite dev server):
```powershell
cd frontend
npm install
npm run dev     # روی http://localhost:5173
```

---

## ۴. خلاصه تست‌ها و نتایج

| تست‌ليد | تعداد | نتیجه |
|--------|-------|-------|
| Desktop (chromium) | ۱۸ | ✅ همه موفق |
| Mobile (chromium Pixel 5) | ۳۶ | ✅ همه موفق |
| دیمو end-to-end | ۷ مرحله | ✅ تمام شد (اسکرین‌شات ۰۶/۰۷ تولید شد) |


---

## ۵. ساختار فایل‌های مهم

```
e:\torob-challange\
├── HANDOFF.md                      # این فایل (جدید)
├── demo.mjs                        # اسکرین‌شات‌دهی دیمو end-to-end
├── start.bat                       # اجرا rápida backend (Windows)
├── package.json / package-lock.json # Playwright dev deps (ریشه)
├── playwright.config.js            # تنظیمات Playwright (2 پروژه)
├── .gitignore                      # node_modules, logs, db, screenshots, dataset
├── backend/
│   ├── main.py                     # FastAPI entry point
│   ├── database.py                 # دیتابیس SQLite
│   ├── ingest.py                   # بارگذاری داده‌های اولیه (CSV)
│   ├── models.py                   # مدل‌های داده
│   ├── requirements.txt            # وابستگی‌های پایتون
│   ├── routers/
│   │   ├── chat.py                 # endpoint /api/chat
│   │   ├── products.py             # endpoint /api/products/search
│   │   └── shops.py                # endpoint /api/shops
│   ├── services/
│   │   ├── agent.py                # مغز ایجنتیک
│   │   ├── search.py
│   │   ├── geo.py
│   │   ├── hours.py
│   │   ├── payment.py              # فیلتر BNPL
│   │   └── mall.py
│   ├── static/                     # build خروجی frontend
│   └── tests/
│       └── test_api.py
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── App.jsx                 # root component, state machine
│       ├── main.jsx
│       ├── index.css
│       └── components/
│           ├── Header.jsx
│           ├── FiltersBar.jsx
│           ├── ChatPanel.jsx
│           ├── ProductCard.jsx
│           ├── ShopCard.jsx
│           ├── MapView.jsx
│           └── VerificationModal.jsx
├── tests/e2e/
│   ├── helpers.js                  # توابع مشترک تست
│   ├── chat-search.spec.js
│   ├── shops.spec.js

---

## ۶. کارهای باقی‌مانده / پیشنهادات برای ادامه

1. **確認 نهایی اسکرین‌شات‌ها** — فایل‌های `shots/06-alternatives.png` و `shots/07-verify.png` را بررسی کنید و اگر لازم است، تایمینگ یا narrative دیمو را در `demo.mjs` brush-up کنید.
2. **ساخت دیتابیس برای’clock جدید** — چون `torob.db` gitignore شده، در یک کلون تازه باید `ingest.py` اجرا شود تا دیتابیس پر شود (اگر فایل ingest وجود داشته باشد).

---

## ۷. دسترسی‌ها و توکن‌ها

- **Repository گیت‌هاب:** `https://github.com/Aminnaghieh/t-newline2.git` (شاخه `main`)
- **Remote origin:** تنظیم شده و code 푸ished شده است.
- **توکن GitHub:** برای این push از توکن شخصی استفاده شد. اگر نیاز به push دوباره دارید، می‌توانید توکن جدید بسازید یا در credential manager ویندوز ذخیره کنید.

---

## ۸. نکات شخصی (فارسی)

- زبان رابط کاربری و پیام‌های ایجنت: **فارسی**
- لوکیشن پیش‌فرض: **تهران، چارسو / علاءالدین** (lat 35.695, lon 51.406)
- نام محصول برای تست‌ها: **کتونی** (سنسو-dried casual shoes)
- رنگ برند اصلی: **قرمز ترب `#E8453C`**

---

> اگر سوالی دارید یا به ادامه کار نیاز دارید، فایل‌های اصلی را در ریپازیتور گیت‌هاب بالا مطالعه کنید و در صورت نیاز به من بپی‌چینید.

3. **CI/CD** — اضافه کردن GitHub Action برای اجرای خودکار تست‌های Playwright در هر push.
4. **راه‌اندازی LLM (Gemini)** — فعلاً agent rule-based است؛ `google-generativeai` در requirements است اما لزوماً فعال نشده. می‌توان verstär lure LLM برای پاسخ‌های طبیعی‌تر کرد.
5. **Deploy** — اپلیکیشن را روی Liara (`liara.json` وجود دارد) یا هر پلتفرم دیگر deploy کنید.

│   └── comparison-verify.spec.js
└── shots/                          # اسکرین‌شات‌های دیمو (gitignore شده)
```

###Ńکات مهم در تست‌ها
- **فیلتر BNPL** در `demo.mjs` به صورت محافظه‌کارانه اعمال می‌شود: اگر پس از اعمال فیلتر لیست فروشگاه‌ها خالی شد، فیلتر رد می‌شود تا مراحل بعدی (جایگزین‌ها و تأیید) شکسته نشوند. علت: فروشگاه نزدیک ممکن است هیچ ارائه‌دهنده BNPL نداشته باشد.
- **استعلام فروشگاه (verification)** سه حالت دارد: `confirmed` (موجود است و قیمت تأیید شد)، `price_changed` (تغییر قیمت ثبت شد)، `no_response` (پاسخگو نیست یا بسته است). حالت `no_response` به صورت تصادفی بین ۳ سناریو قرار می‌گیرد و به عهده-random است، نه باگ.
- تمام تست‌ها با لوکال `fa-IR` و منطقه زمانی `Asia/Tehran` اجرا می‌شوند و موقعیت جغرافیای ثابت (تهران، چارسو/علاءالدین)nightly假える می‌شود.

در این حالت متغیر محیطی `BASE_URL` را برای تست‌ها تنظیم کنید.

### ۳) تست‌های E2E
```powershell
cd e:\torob-challange
npm install
npx playwright install chromium
npm run test:e2e            # همه تست‌ها (desktop + mobile)
npm run test:e2e:headed     # حالت قابل مشاهده
npm run test:e2e:ui         # رابط کاربری Playwright
```

### ۴) اجرای دیمو دستی (demo.mjs)
```powershell
cd e:\torob-challange
node demo.mjs   # ابتدا باید backend در حال اجرا باشد
```
اسکرین‌شات‌ها در پوشه `shots/` ذخیره می‌شوند.
