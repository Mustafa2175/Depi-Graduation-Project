import { test, expect } from '@playwright/test';

test.describe('Landing Page', () => {
  test('should render correctly at root URL', async ({ page }) => {
    await page.goto('/');

    // 1. URL should be root
    await expect(page).toHaveURL('/');

    // 2. Headline must contain expected text
    const headline = page.locator('h1');
    await expect(headline).toBeVisible({ timeout: 10000 });
    await expect(headline).toContainText("Egypt's Tech Job Market,");
    await expect(headline).toContainText('Decoded in Real-Time');

    // 3. Subheadline visible
    const sub = page.getByText('Scraping 190+ job postings daily');
    await expect(sub).toBeVisible();

    // 4. "Explore the Dashboard" CTA button visible
    const heroBtn = page.getByRole('button', { name: /Explore the Dashboard/i });
    await expect(heroBtn).toBeVisible();

    // 5. No dashboard link in floating navbar (removed), no sidebar
    const sidebar = page.locator('.sidebar');
    await expect(sidebar).not.toBeVisible();
  });

  test('should navigate to /dashboard when clicking "Go to Dashboard"', async ({ page }) => {
    await page.goto('/');

    // Click the hero CTA button
    const heroBtn = page.getByRole('button', { name: /Explore the Dashboard/i });
    await heroBtn.click();

    // URL must change to /dashboard
    await expect(page).toHaveURL(/\/dashboard$/, { timeout: 8000 });

    // Sidebar must now be visible (it's part of the dashboard layout)
    const sidebar = page.locator('.sidebar');
    await expect(sidebar).toBeVisible({ timeout: 8000 });

    // Sidebar brand title visible
    const brand = page.locator('.sidebar-brand h1');
    await expect(brand).toBeVisible();
    await expect(brand).toContainText('Job Market Tracker');
  });

  test('should show stat pills with project data', async ({ page }) => {
    await page.goto('/');

    // Live data badge in top bar
    const liveBadge = page.getByText('Live Data');
    await expect(liveBadge).toBeVisible({ timeout: 10000 });

    // Stat pills about job postings
    const statPill = page.getByText('190+ Job Postings Tracked');
    await expect(statPill).toBeVisible();
  });
});
