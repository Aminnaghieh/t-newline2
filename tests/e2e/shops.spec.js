import { test, expect } from '@playwright/test';
import { gotoApp, waitForReply, assistantMessages, readShopCount, selectFirstProduct } from './helpers.js';

test.describe('کشف فروشگاه‌های نزدیک', () => {
  test.beforeEach(async ({ page }) => {
    await gotoApp(page);
  });

  test('انتخاب محصول → فهرست فروشگاه‌های نزدیک', async ({ page }) => {
    await selectFirstProduct(page);

    // The shop tab must be active and the shop list populated.
    await expect(page.getByTestId('shop-card').first()).toBeVisible({ timeout: 15_000 });

    const count = await readShopCount(page);
    expect(count).toBeGreaterThan(0);
  });

  test('فیلتر شعاع ۱ کیلومتر → fallback خودکار به شعاع بزرگ‌تر', async ({ page }) => {
    await selectFirstProduct(page);

    const radiusSelect = page.locator('select').filter({ hasText: 'کیلومتر' }).first();
    await radiusSelect.selectOption('1');

    await waitForReply(page);
    const text = await assistantMessages(page);

    // Either a shop was found within 1 km, or the agent widened the radius
    // and said so explicitly.
    expect(text).toMatch(/کیلومتر/);
  });

  test('فیلتر اقساطی: انتخاب ارائه‌دهنده نتایج را محدود می‌کند', async ({ page }) => {
    await selectFirstProduct(page);

    const before = (await readShopCount(page)) ?? 0;

    await page.getByRole('button', { name: 'ترب‌پی', exact: true }).click();
    await waitForReply(page);

    const text = await assistantMessages(page);
    expect(text.length).toBeGreaterThan(10);

    // Filter is now reflected in the active-filter counter.
    await expect(page.getByText('پاک کردن فیلترها')).toBeVisible();

    if (before > 0) {
      const after = (await readShopCount(page)) ?? 0;
      expect(after).toBeLessThanOrEqual(before);
    }
  });

  test('فیلتر «فقط فروشگاه‌های باز» فعال می‌شود', async ({ page }) => {
    await selectFirstProduct(page);

    await page.getByRole('button', { name: 'فقط فروشگاه‌های باز' }).click();
    await waitForReply(page);

    await expect(page.getByText('پاک کردن فیلترها')).toBeVisible();
    await expect(page.getByText('فقط فروشگاه‌های باز')).toBeVisible();
  });

  test('سقف بودجه در نوار فیلتر قابل انتخاب است', async ({ page }) => {
    await gotoApp(page);
    const budgetSelect = page.locator('select').filter({ hasText: 'میلیون' }).first();
    await expect(budgetSelect).toBeVisible();
    await budgetSelect.selectOption('3000000');
    await expect(budgetSelect).toHaveValue('3000000');
  });

  test('پاک کردن فیلترها همه را ریست می‌کند', async ({ page }) => {
    await selectFirstProduct(page);
    await page.getByRole('button', { name: 'فقط فروشگاه‌های باز' }).click();
    await waitForReply(page);
    await expect(page.getByText('پاک کردن فیلترها')).toBeVisible();

    await page.getByRole('button', { name: 'پاک کردن فیلترها' }).click();
    await waitForReply(page);
    await expect(page.getByText('پاک کردن فیلترها')).toBeHidden();
  });
});
