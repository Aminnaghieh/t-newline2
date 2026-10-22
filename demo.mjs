import { chromium } from '@playwright/test';

const BASE = process.env.BASE_URL || 'http://127.0.0.1:8000';

const browser = await chromium.launch({ headless: false });
const ctx = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  locale: 'fa-IR',
  timezoneId: 'Asia/Tehran',
  permissions: ['geolocation'],
  geolocation: { latitude: 35.695, longitude: 51.406 },
});
const page = await ctx.newPage();

const log = (...a) => console.log('•', ...a);
const shot = async (name) => {
  await page.screenshot({ path: `shots/${name}.png` });
  log(`📸 ${name}`);
};

await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(2500);
await shot('01-home');

// ── 1. جستجوی محصول ──────────────────────────────────────────────
const input = page.getByPlaceholder(/چه محصولی مدنظرتونه/);
await input.fill('کتونی');
await input.press('Enter');
await page.waitForTimeout(4500);
await shot('02-search');

// ── 2. یافتن فروشگاه‌ها ─────────────────────────────────────────
await page.getByTestId('find-shops-btn').first().click();
await page.waitForTimeout(6000);
await shot('03-shops');
log(`تعداد کارت فروشگاه: ${await page.getByTestId('shop-card').count()}`);

// ── 3. فیلتر «فقط فروشگاه‌های باز» ────────────────────────────────
const openBtn = page.getByRole('button', { name: /فقط فروشگاه‌های باز/ });
if (await openBtn.count()) {
  await openBtn.first().click();
  await page.waitForTimeout(4500);
  await shot('04-filter-open');
  log(`پس از فیلتر «فقط باز»: ${await page.getByTestId('shop-card').count()} فروشگاه`);
}

// ── 4. فیلتر خرید اقساطی ─────────────────────────────────────────
// The nearby shop may not support any BNPL, which would empty the list and
// break the alternatives/verification steps below. Only apply the BNPL
// filter if something is actually left afterwards.
const bnplBtn = page.getByRole('button', { name: /^اسنپ‌پی$/ });
if (await bnplBtn.count()) {
  await bnplBtn.first().click();
  await page.waitForTimeout(4500);
  const after = await page.getByTestId('shop-card').count();
  await shot('05-filter-bnpl');
  log(`پس از فیلتر BNPL: ${after} فروشگاه`);
  if (after === 0) {
    log('هیچ فروشگاهی با این BNPL نیست — فیلتر را برمی‌دارم');
    await bnplBtn.first().click();
    await page.waitForTimeout(4500);
  }
}

// ── 5. جایگزین‌ها ───────────────────────────────────────────────
const altBtn = page.getByTestId('alternatives-btn').first();
if (await altBtn.count()) {
  await altBtn.click();
  await page.waitForTimeout(7000);
  await shot('06-alternatives');
  log(`پس از جایگزین: ${await page.getByTestId('shop-card').count()} فروشگاه`);
} else {
  log('⚠️ دکمه جایگزین پیدا نشد');
}

// ── 6. تأیید فروشگاه ────────────────────────────────────────────
const verifyBtn = page.getByTestId('verify-shop-btn').first();
if (await verifyBtn.count()) {
  await verifyBtn.click();
  await page.waitForTimeout(7000);
  await shot('07-verify');
  log('مودال تأیید فروشگاه');
} else {
  log('⚠️ دکمه تأیید پیدا نشد');
}

console.log('\n✅ تمام شد — مرورگر باز است. برای بستن پنجره کلیک کنید.');
await page.waitForTimeout(90000);
await browser.close();
