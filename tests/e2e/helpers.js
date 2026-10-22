import { expect } from '@playwright/test';

/**
 * Shared helpers for the TorobGard e2e suite.
 */

/** The app boots on the "products" tab and renders an initial catalog. */
export async function gotoApp(page) {
  await page.goto('/', { waitUntil: 'domcontentloaded' });
  // The header brand is the reliable "app is mounted" signal.
  await expect(page.getByRole('banner').getByText('تُرب‌گرد')).toBeVisible();
  // The stepper is the second signal.
  await expect(page.getByText('۱. انتخاب کالا')).toBeVisible();
}

/** Type a message into the chat input and submit it. */
export async function sendChat(page, text) {
  const input = page.getByPlaceholder(/چه محصولی مدنظرتونه/);
  await input.fill(text);
  await input.press('Enter');
}

/** Wait until the assistant has finished replying (loading indicator gone). */
export async function waitForReply(page) {
  await expect(page.getByText('دستیار در حال جستجو و تحلیل اطلاعات')).toBeHidden({ timeout: 25_000 });
}

/** The chat bubble area (assistant messages only). */
export function chatArea(page) {
  return page.locator('.markdown-body-assistant');
}

/** Read all assistant messages as plain text. */
export async function assistantMessages(page) {
  return (await chatArea(page).allTextContents()).join('\n---\n');
}

/** Switch the dashboard tab strip. */
export async function openTab(page, label) {
  await page.getByRole('button', { name: new RegExp(label) }).first().click();
}

/** Grant a fixed geolocation and trigger the GPS button. */
export async function detectLocation(page, lat = 35.695, lon = 51.406) {
  await page.context().setGeolocation({ latitude: lat, longitude: lon });
  await page.getByTitle('موقعیت فعلی من (GPS)').click();
}

/** The dashboard product-card grid. */
export function productCards(page) {
  return page.getByTestId('product-card');
}

/** The dashboard shop-card list. */
export function shopCards(page) {
  return page.getByTestId('shop-card');
}

/**
 * Click the first product's "find shops" button and wait for the shop list.
 *
 * The agent may widen the radius server-side (5 → 10 → 20 km) when nothing
 * is found nearby, so we wait for a real shop card rather than for a fixed
 * number of results.
 */
export async function selectFirstProduct(page) {
  await sendChat(page, 'کتونی');
  await waitForReply(page);
  await openTab(page, 'کشف و مقایسه مدل‌ها');
  await page.getByTestId('find-shops-btn').first().click();
  await expect(page.getByRole('button', { name: /فروشگاه‌های حضوری/ })).toBeVisible();
  await expect(page.getByTestId('shop-card').first()).toBeVisible({ timeout: 20_000 });
}

/** Read the visible product count in the chat reply. */
export async function readReplyCount(page) {
  const text = await assistantMessages(page);
  const m = text.match(/(\d+)\s+محصول/);
  return m ? Number(m[1]) : null;
}

/** Read the visible shop count in the chat reply. */
export async function readShopCount(page) {
  const text = await assistantMessages(page);
  // The agent writes "🏪 **N فروشگاه** ..." — but it may also mention
  // "N فروشگاه جایگزین" for the alternatives flow.
  const m = text.match(/(\d+)\s+فروشگاه/);
  return m ? Number(m[1]) : null;
}
