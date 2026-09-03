import { expect, test } from '@playwright/test';

test('login smoke reaches dashboard', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveURL(/\/login/);

  await page.locator('input[type="email"]').fill('smoke@example.com');
  await page.locator('input[type="password"]').fill('smoke-password-123');
  await page.getByRole('button', { name: '登录' }).click();

  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole('heading', { name: '研股工作台' })).toBeVisible();
});
