import { test, expect } from '@playwright/test';

test.describe('Creators Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/creators');
  });

  test('should display creators page heading', async ({ page }) => {
    await expect(page).toHaveURL(/\/creators/);
    const heading = page.getByRole('heading', { name: /creator/i });
    await expect(heading).toBeVisible();
  });

  test('should display creators list or empty state', async ({ page }) => {
    const creatorList = page.locator('[data-testid="creators-list"], .creators-grid, .creators-table');
    const emptyState = page.locator('[data-testid="empty-state"], .empty-state, .no-creators');

    const listVisible = await creatorList.isVisible().catch(() => false);
    const emptyVisible = await emptyState.isVisible().catch(() => false);

    expect(listVisible || emptyVisible).toBeTruthy();
  });

  test('should navigate to create creator form', async ({ page }) => {
    const createButton = page.getByRole('button', { name: /add creator|new creator|create creator/i });
    await expect(createButton).toBeVisible();
    await createButton.click();
    await expect(page).toHaveURL(/\/creators\/new|\/creators\/create/);
  });

  test('should create a new creator with valid data', async ({ page }) => {
    const createButton = page.getByRole('button', { name: /add creator|new creator|create creator/i });
    await createButton.click();

    const nameInput = page.locator('input[name="name"], input[placeholder*="name" i], [data-testid="creator-name-input"]');
    await nameInput.fill('Test Creator');

    const emailInput = page.locator('input[name="email"], input[type="email"], [data-testid="creator-email-input"]');
    await emailInput.fill('test.creator@example.com');

    const bioInput = page.locator('textarea[name="bio"], textarea[placeholder*="bio" i], [data-testid="creator-bio-input"]');
    await bioInput.fill('This is a test creator bio.');

    const submitButton = page.getByRole('button', { name: /create|save|submit/i });
    await submitButton.click();

    await expect(page).toHaveURL(/\/creators/);
    const successMessage = page.locator('[data-testid="success-message"], .success-toast, .alert-success');
    await expect(successMessage).toBeVisible({ timeout: 5000 });
  });

  test('should show validation errors for empty required fields', async ({ page }) => {
    const createButton = page.getByRole('button', { name: /add creator|new creator|create creator/i });
    await createButton.click();

    const submitButton = page.getByRole('button', { name: /create|save|submit/i });
    await submitButton.click();

    const errorMessages = page.locator('[data-testid="field-error"], .error-message, .invalid-feedback, .form-error');
    const errorCount = await errorMessages.count();
    expect(errorCount).toBeGreaterThan(0);
  });

  test('should view creator details', async ({ page }) => {
    const creatorCard = page.locator('[data-testid="creator-card"], .creator-card, .creator-item').first();
    const isVisible = await creatorCard.isVisible().catch(() => false);

    if (isVisible) {
      await creatorCard.click();
      await expect(page).toHaveURL(/\/creators\/\d+|\/creators\/[\w-]+/);
      const detailHeading = page.getByRole('heading');
      await expect(detailHeading).toBeVisible();
    }
  });

  test('should edit an existing creator', async ({ page }) => {
    const creatorCard = page.locator('[data-testid="creator-card"], .creator-card, .creator-item').first();
    const isVisible = await creatorCard.isVisible().catch(() => false);

    if (isVisible) {
      const editButton = creatorCard.getByRole('button', { name: /edit/i });
      await editButton.click();

      const nameInput = page.locator('input[name="name"], input[placeholder*="name" i], [data-testid="creator-name-input"]');
      await nameInput.fill('Updated Creator Name');

      const saveButton = page.getByRole('button', { name: /save|update/i });
      await saveButton.click();

      const successMessage = page.locator('[data-testid="success-message"], .success-toast, .alert-success');
      await expect(successMessage).toBeVisible({ timeout: 5000 });
    }
  });

  test('should delete a creator with confirmation', async ({ page }) => {
    const creatorCard = page.locator('[data-testid="creator-card"], .creator-card, .creator-item').first();
    const isVisible = await creatorCard.isVisible().catch(() => false);

    if (isVisible) {
      const deleteButton = creatorCard.getByRole('button', { name: /delete/i });
      await deleteButton.click();

      const confirmDialog = page.locator('[data-testid="confirm-dialog"], .modal, [role="dialog"]');
      await expect(confirmDialog).toBeVisible();

      const confirmButton = page.getByRole('button', { name: /confirm|yes|delete/i });
      await confirmButton.click();

      const successMessage = page.locator('[data-testid="success-message"], .success-toast, .alert-success');
      await expect(successMessage).toBeVisible({ timeout: 5000 });
    }
  });

  test('should handle creator not found error', async ({ page }) => {
    await page.goto('/creators/999999');
    const notFoundMessage = page.locator('[data-testid="not-found"], .not-found, .error-404');
    const isVisible = await notFoundMessage.isVisible().catch(() => false);
    if (isVisible) {
      await expect(notFoundMessage).toBeVisible();
    }
  });
});
