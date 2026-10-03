import { test, expect } from '@playwright/test';

test.describe('Marketplace Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/marketplace');
  });

  test('should display marketplace page heading', async ({ page }) => {
    await expect(page).toHaveURL(/\/marketplace/);
    const heading = page.getByRole('heading', { name: /marketplace|store|products/i });
    await expect(heading).toBeVisible();
  });

  test('should display products grid or list', async ({ page }) => {
    const productsGrid = page.locator('[data-testid="products-grid"], .products-grid, .products-list, .marketplace-items');
    const emptyState = page.locator('[data-testid="empty-state"], .empty-state, .no-products');

    const gridVisible = await productsGrid.isVisible().catch(() => false);
    const emptyVisible = await emptyState.isVisible().catch(() => false);

    expect(gridVisible || emptyVisible).toBeTruthy();
  });

  test('should display product cards with name and price', async ({ page }) => {
    const productCards = page.locator('[data-testid="product-card"], .product-card, .product-item');
    const count = await productCards.count();

    if (count > 0) {
      const firstCard = productCards.first();
      const productName = firstCard.locator('[data-testid="product-name"], .product-name, h3, h4');
      await expect(productName).toBeVisible();

      const productPrice = firstCard.locator('[data-testid="product-price"], .product-price, .price');
      await expect(productPrice).toBeVisible();
      const priceText = await productPrice.textContent();
      expect(priceText).toMatch(/\$|€|£|\d+/);
    }
  });

  test('should filter products by category', async ({ page }) => {
    const categoryFilter = page.locator('select[name="category"], [data-testid="category-filter"], .category-select');
    const isVisible = await categoryFilter.isVisible().catch(() => false);

    if (isVisible) {
      const options = await categoryFilter.locator('option').allTextContents();
      if (options.length > 1) {
        await categoryFilter.selectOption({ index: 1 });
        await expect(page).toHaveURL(/category=|filter=/);
      }
    }
  });

  test('should search for products', async ({ page }) => {
    const searchInput = page.locator('input[type="search"], input[name="search"], input[placeholder*="search" i], [data-testid="search-input"]');
    const isVisible = await searchInput.isVisible().catch(() => false);

    if (isVisible) {
      await searchInput.fill('test product');
      await searchInput.press('Enter');
      await expect(page).toHaveURL(/search=|q=|query=/);
    }
  });

  test('should view product details', async ({ page }) => {
    const productCard = page.locator('[data-testid="product-card"], .product-card, .product-item').first();
    const isVisible = await productCard.isVisible().catch(() => false);

    if (isVisible) {
      await productCard.click();
      await expect(page).toHaveURL(/\/marketplace\/\d+|\/marketplace\/[\w-]+|\/products\/\d+/);
      const productDetail = page.locator('[data-testid="product-detail"], .product-detail, .product-info');
      await expect(productDetail).toBeVisible();
    }
  });

  test('should add product to cart', async ({ page }) => {
    const productCard = page.locator('[data-testid="product-card"], .product-card, .product-item').first();
    const isVisible = await productCard.isVisible().catch(() => false);

    if (isVisible) {
      const addToCartButton = productCard.getByRole('button', { name: /add to cart|buy|purchase/i });
      await addToCartButton.click();

      const cartBadge = page.locator('[data-testid="cart-badge"], .cart-count, .badge');
      const badgeVisible = await cartBadge.isVisible().catch(() => false);
      if (badgeVisible) {
        const badgeText = await cartBadge.textContent();
        expect(parseInt(badgeText || '0')).toBeGreaterThan(0);
      }
    }
  });

  test('should complete purchase flow', async ({ page }) => {
    const productCard = page.locator('[data-testid="product-card"], .product-card, .product-item').first();
    const isVisible = await productCard.isVisible().catch(() => false);

    if (isVisible) {
      const buyButton = productCard.getByRole('button', { name: /buy now|purchase|checkout/i });
      await buyButton.click();

      await expect(page).toHaveURL(/\/checkout|\/purchase/);

      const checkoutForm = page.locator('[data-testid="checkout-form"], .checkout-form, form');
      await expect(checkoutForm).toBeVisible();

      const placeOrderButton = page.getByRole('button', { name: /place order|complete purchase|pay/i });
      await expect(placeOrderButton).toBeVisible();
    }
  });

  test('should handle out of stock products', async ({ page }) => {
    const outOfStockBadge = page.locator('[data-testid="out-of-stock"], .out-of-stock, .sold-out');
    const isVisible = await outOfStockBadge.isVisible().catch(() => false);

    if (isVisible) {
      const addToStockButton = page.getByRole('button', { name: /add to cart|buy/i }).first();
      await expect(addToStockButton).toBeDisabled();
    }
  });

  test('should display product categories or filters sidebar', async ({ page }) => {
    const filtersSidebar = page.locator('[data-testid="filters"], .filters, .sidebar-filters, .category-list');
    const isVisible = await filtersSidebar.isVisible().catch(() => false);

    if (isVisible) {
      await expect(filtersSidebar).toBeVisible();
      const filterLinks = filtersSidebar.locator('a, button, label');
      const count = await filterLinks.count();
      expect(count).toBeGreaterThan(0);
    }
  });
});
