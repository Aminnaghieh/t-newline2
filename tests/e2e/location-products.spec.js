import { test, expect } from '@playwright/test';
import { gotoApp, sendChat, waitForReply, readReplyCount } from './helpers.js';

/**
 * Location-aware product discovery.
 *
 * The catalog is refetched (debounced ~400ms) whenever the user's location
 * changes – even with no product selected – and each card carries nearby
 * availability: registered (not confirmed) nearby price, nearest distance
 * and an "outside your area" badge for fallback items.
 */
test.describe('کشف محصول بر اساس موقعیت مکانی', () => {
  test.beforeEach(async ({ page }) => {
    await gotoApp(page);
  });

  test('تغییر لوکیشن چارسو ↔ سعادت‌آباد لیست محصولات را عوض می‌کند', async ({ page }) => {
    // Register the response listeners BEFORE navigating, then reload the app
    // so the initial located catalog fetch is captured deterministically
    // (no race with the beforeEach navigation).
    const charsuResp = page.waitForResponse(
      (r) => r.url().includes('/api/products/search?') && r.url().includes('lat=35.695')
    );
    await gotoApp(page);
    const before = await (await charsuResp).json();
    expect(before.products.length).toBeGreaterThan(0);

    // Switch to Saadat Abad and capture the debounced refetch
    const saadatResp = page.waitForResponse(
      (r) => r.url().includes('/api/products/search?') && r.url().includes('lat=35.7789')
    );
    await page.getByLabel('انتخاب محله').selectOption('saadatabad');
    const after = await (await saadatResp).json();

    // The catalog genuinely re-queried with the new coordinates.
    // (DOM text can legitimately repeat when the same commodity product is
    // sold next to both locations, so compare the data, not the pixels.)
    expect(after.products.map((p) => p.product_id)).not.toEqual(
      before.products.map((p) => p.product_id)
    );
    expect(after.products[0].nearby_shops_count).toBeGreaterThan(0);
    expect(after.products[0].in_radius).toBe(true);

    // Cards were re-rendered with the new data and expose nearby fields
    await expect(page.getByTestId('product-card').first()).toContainText(
      /فروشگاه نزدیک|نزدیک‌ترین/
    );
  });

  test('نقطه بدون فروشگاه در دیتاست → محصولات جایگزین + بنر + نشان خارج از محدوده', async ({
    page,
  }) => {
    // Northeast Tehran: verified 0 dataset shops within 5 km, many within 25 km.
    await page.context().setGeolocation({ latitude: 35.831, longitude: 51.523 });
    await page.getByTitle('موقعیت فعلی من (GPS)').click();

    await expect(page.getByTestId('products-fallback-banner')).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId('product-card').first()).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId('out-of-radius-badge').first()).toContainText('خارج از محدوده');
  });

  test('پیام چت همچنان لیست محصولات را به‌روز می‌کند (حالا با فیلدهای نزدیکی)', async ({
    page,
  }) => {
    await sendChat(page, 'کتونی');
    await waitForReply(page);

    const count = await readReplyCount(page);
    expect(count).toBeGreaterThan(0);

    await expect(page.getByTestId('product-card').first()).toBeVisible({ timeout: 15_000 });
    // Nearby fields rendered on chat-driven results too
    await expect(page.getByTestId('product-card').first()).toContainText('فروشگاه نزدیک');
  });
});
