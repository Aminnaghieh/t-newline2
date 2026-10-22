/**
 * Debug probe: dumps what the app actually renders so we can align the
 * e2e locators with the real DOM. Run with:
 *   node tests/e2e/probe.mjs
 */
import { chromium } from '@playwright/test';

const BASE = process.env.BASE_URL || 'http://127.0.0.1:8000';

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

page.on('console', (m) => console.log(`[console.${m.type()}]`, m.text()));
page.on('pageerror', (e) => console.log('[pageerror]', String(e)));

await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(2500);

const dump = async (label) => {
  console.log(`\n===== ${label} =====`);
  console.log('BUTTONS:');
  const btns = await page.locator('button').evaluateAll((els) =>
    els.map((e) => ({
      text: (e.innerText || '').trim().replace(/\s+/g, ' ').slice(0, 60),
      cls: e.className.slice(0, 60),
    }))
  );
  btns.forEach((b, i) => console.log(`  [${i}] "${b.text}" | ${b.cls}`));

  console.log('PRODUCT-BUTTONS (has تومان):', await page.locator('button:has-text("تومان")').count());
  console.log('SELECTS:', await page.locator('select').count());
  console.log('MARKDOWN-BODY:', await page.locator('.markdown-body').count());
  const md = await page.locator('.markdown-body').allTextContents();
  md.forEach((m, i) => console.log(`  md[${i}]: ${m.replace(/\s+/g, ' ').slice(0, 300)}`));
};

await dump('INITIAL');

// Send a chat message
const input = page.getByPlaceholder(/چه محصولی مدنظرتونه/);
await input.fill('کتونی');
await input.press('Enter');
await page.waitForTimeout(4000);
await dump('AFTER CHAT');

// Try clicking the first product card
const cards = page.locator('button:has-text("تومان")');
console.log('\n>>> product card count:', await cards.count());
if (await cards.count()) {
  console.log('>>> first card text:', (await cards.first().innerText()).replace(/\s+/g, ' ').slice(0, 120));
  await cards.first().click();
  await page.waitForTimeout(4000);
  await dump('AFTER PRODUCT CLICK');
}

await page.screenshot({ path: 'probe.png', fullPage: true });
await browser.close();
console.log('\ndone -> probe.png');
