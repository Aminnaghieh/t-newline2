import { test, expect } from '@playwright/test';
import {
  gotoApp,
  sendChat,
  waitForReply,
  assistantMessages,
  readReplyCount,
  readShopCount,
  openTab,
  selectFirstProduct,
} from './helpers.js';

test.describe('گفتگو و جستجوی طبیعی', () => {
  test.beforeEach(async ({ page }) => {
    await gotoApp(page);
  });

  test('بارگذاری اولیه: پیام خوش‌آمد و کاتالوگ اولیه', async ({ page }) => {
    await expect(page.getByText('سلام!')).toBeVisible();
    await expect(page.getByRole('button', { name: /کشف و مقایسه مدل‌ها/ })).toBeVisible();

    // The initial product fetch must populate the catalog grid.
    await expect(page.getByTestId('product-card').first()).toBeVisible({ timeout: 15_000 });
  });

  test('کوئری طبیعی فارسی: بودجه/اقساط/محله از متن جدا می‌شود', async ({ page }) => {
    await sendChat(
      page,
      'یه کتونی راحت برای پیاده روی تا ۳ میلیون با اسنپ پی میخوام نزدیک چارسو'
    );
    await waitForReply(page);

    const text = await assistantMessages(page);

    // The product query must be normalized to just "کتونی" (not the whole sentence).
    expect(text).toContain('«کتونی»');
    expect(text).not.toContain('«یه کتونی راحت');

    // The budget must be extracted and shown separately.
    expect(text).toMatch(/بودجه:\s*3\s*میلیون\s*تومان/);

    const count = await readReplyCount(page);
    expect(count).toBeGreaterThan(0);
  });

  test('جستجوی محصول بدون بودجه هم نتیجه می‌دهد', async ({ page }) => {
    await sendChat(page, 'کفش کتونی');
    await waitForReply(page);
    expect(await readReplyCount(page)).toBeGreaterThan(0);
  });

  test('پیام خوش‌آمد بدون محصول: دسته‌های پیشنهادی', async ({ page }) => {
    await sendChat(page, 'سلام');
    await waitForReply(page);
    const text = await assistantMessages(page);
    expect(text.length).toBeGreaterThan(10);
  });

  test('کوئری بی‌نتیجه پیام مناسب می‌دهد (نه خطا)', async ({ page }) => {
    await sendChat(page, 'اسکوتر الکتریکی فضایی');
    await waitForReply(page);
    const text = await assistantMessages(page);
    expect(text.length).toBeGreaterThan(10);
    await expect(page.getByText('ارتباط با سرور برقرار نشد')).toBeHidden();
  });

  test('کلیک روی محصول → تب فروشگاه‌ها فعال می‌شود', async ({ page }) => {
    await selectFirstProduct(page);
    const shopTab = page.getByRole('button', { name: /فروشگاه‌های حضوری/ });
    // The shop tab is highlighted (active) — it carries the red background.
    await expect(shopTab).toHaveClass(/bg-\[#E8453C\]/);
  });
});
