import { test, expect } from '@playwright/test';
import {
  gotoApp,
  sendChat,
  waitForReply,
  assistantMessages,
  openTab,
  detectLocation,
  selectFirstProduct,
} from './helpers.js';

test.describe('مقایسه و استعلام', () => {
  test.beforeEach(async ({ page }) => {
    await gotoApp(page);
  });

  test('استعلام قیمت: مودال باز می‌شود و نتیجه را نشان می‌دهد', async ({ page }) => {
    await selectFirstProduct(page);

    await page.getByTestId('verify-shop-btn').first().click();

    await expect(page.getByText('استعلام هوشمند ایجنت با فروشگاه')).toBeVisible({ timeout: 20_000 });

    const hasConfirmed = await page
      .getByText('کالا موجود است و قیمت تأیید شد')
      .isVisible()
      .catch(() => false);
    const hasPriceChanged = await page
      .getByText('تغییر قیمت ثبت شد')
      .isVisible()
      .catch(() => false);
    const hasNoResponse = await page
      .getByText('فروشگاه پاسخگو نیست یا بسته است')
      .isVisible()
      .catch(() => false);

    expect(hasConfirmed || hasPriceChanged || hasNoResponse).toBeTruthy();

    await page.getByRole('button', { name: 'بستن' }).click();
    await expect(page.getByText('استعلام هوشمند ایجنت با فروشگاه')).toBeHidden();
  });

  test('مقایسه: جایگزین‌های نزدیک نمایش داده می‌شوند', async ({ page }) => {
    await selectFirstProduct(page);

    await page.getByTestId('alternatives-btn').first().click();
    await waitForReply(page);

    const text = await assistantMessages(page);
    expect(text).toMatch(/فروشگاه/);
  });
});

test.describe('تجربه کاربری و ریسپانسیو', () => {
  test('انتخاب محله از هدر موقعیت را تغییر می‌دهد', async ({ page }) => {
    await gotoApp(page);
    const areaSelect = page.getByLabel('انتخاب محله');
    await expect(areaSelect).toBeVisible();
    await areaSelect.selectOption('vanak');
    await expect(areaSelect).toHaveValue('vanak');
  });

  test('دکمه GPS موقعیت را تشخیص می‌دهد', async ({ page }) => {
    await gotoApp(page);
    await detectLocation(page);
    await expect(page.getByTitle('موقعیت فعلی من (GPS)')).toBeEnabled({ timeout: 15_000 });
  });

  test('تب نقشه: مارکرها رندر می‌شوند', async ({ page }) => {
    await gotoApp(page);
    await selectFirstProduct(page);

    await openTab(page, 'نقشه');
    await expect(page.locator('.leaflet-container')).toBeVisible({ timeout: 15_000 });
    await expect(page.locator('.leaflet-marker-icon').first()).toBeVisible({ timeout: 15_000 });
  });

  test('بدون خطای کنسول در بارگذاری', async ({ page }) => {
    const errors = [];
    page.on('console', (m) => {
      if (m.type() === 'error') errors.push(m.text());
    });
    page.on('pageerror', (e) => errors.push(String(e)));

    await gotoApp(page);
    await sendChat(page, 'کتونی');
    await waitForReply(page);

    const real = errors.filter(
      (e) => !/tile|openstreetmap|leaflet|font|Failed to load resource/i.test(e)
    );
    expect(real).toEqual([]);
  });
});
