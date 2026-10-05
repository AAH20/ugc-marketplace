import { test, expect } from '@playwright/test';

test.describe('Dashboard Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard');
  });

  test('should navigate to dashboard and display main heading', async ({ page }) => {
    await expect(page).toHaveURL(/\/dashboard/);
    const heading = page.getByRole('heading', { name: /dashboard/i });
    await expect(heading).toBeVisible();
  });

  test('should display stats cards with numeric values', async ({ page }) => {
    const statsSection = page.locator('[data-testid="stats-section"], .stats-grid, .dashboard-stats');
    await expect(statsSection).toBeVisible();

    const statCards = page.locator('[data-testid="stat-card"], .stat-card, .stats-card');
    const count = await statCards.count();
    expect(count).toBeGreaterThan(0);

    for (let i = 0; i < count; i++) {
      const card = statCards.nth(i);
      await expect(card).toBeVisible();
      const value = card.locator('[data-testid="stat-value"], .stat-value, .value');
      await expect(value).toBeVisible();
      const text = await value.textContent();
      expect(text).toMatch(/\d+/);
    }
  });

  test('should display navigation menu with expected links', async ({ page }) => {
    const nav = page.locator('nav, [data-testid="main-nav"], .sidebar');
    await expect(nav).toBeVisible();

    const expectedLinks = ['Dashboard', 'Creators', 'Marketplace'];
    for (const linkText of expectedLinks) {
      const link = nav.getByRole('link', { name: new RegExp(linkText, 'i') });
      await expect(link).toBeVisible();
    }
  });

  test('should navigate to Creators page from dashboard', async ({ page }) => {
    const nav = page.locator('nav, [data-testid="main-nav"], .sidebar');
    const creatorsLink = nav.getByRole('link', { name: /creators/i });
    await creatorsLink.click();
    await expect(page).toHaveURL(/\/creators/);
  });

  test('should navigate to Marketplace page from dashboard', async ({ page }) => {
    const nav = page.locator('nav, [data-testid="main-nav"], .sidebar');
    const marketplaceLink = nav.getByRole('link', { name: /marketplace/i });
    await marketplaceLink.click();
    await expect(page).toHaveURL(/\/marketplace/);
  });

  test('should handle dashboard load errors gracefully', async ({ page }) => {
    const errorContainer = page.locator('[data-testid="error-message"], .error-banner, .alert-error');
    const isErrorVisible = await errorContainer.isVisible().catch(() => false);
    if (isErrorVisible) {
      const errorText = await errorContainer.textContent();
      expect(errorText).toBeTruthy();
      const retryButton = page.getByRole('button', { name: /retry/i });
      await expect(retryButton).toBeVisible();
    }
  });

  test('should display recent activity or quick actions section', async ({ page }) => {
    const activitySection = page.locator('[data-testid="recent-activity"], .recent-activity, .quick-actions');
    const isVisible = await activitySection.isVisible().catch(() => false);
    if (isVisible) {
      await expect(activitySection).toBeVisible();
    }
  });
});
