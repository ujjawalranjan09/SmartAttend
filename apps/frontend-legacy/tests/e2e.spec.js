/**
 * SmartAttend E2E Tests (Playwright)
 * Tests core user flows: login, attendance marking, analytics, admin management.
 *
 * Run with: npx playwright test
 */

const { test, expect } = require('@playwright/test');

const BASE = 'http://localhost:8000';

// Test credentials — ensure these exist in the seed data
const STUDENT = { email: 'student@test.edu', password: 'student123' };
const FACULTY = { email: 'faculty@test.edu', password: 'faculty123' };

test.describe('Authentication', () => {
  test('should login as student and see dashboard', async ({ page }) => {
    await page.goto('http://localhost:8080');
    await page.fill('[type="email"]', STUDENT.email);
    await page.fill('[type="password"]', STUDENT.password);
    await page.click('button[type="submit"]');

    // Wait for dashboard to load
    await expect(page.locator('.page-title')).toHaveText(/Dashboard|My Dashboard/);
    await expect(page.locator('.kpi-grid')).toBeVisible();
  });

  test('should show error on invalid credentials', async ({ page }) => {
    await page.goto('http://localhost:8080');
    await page.fill('[type="email"]', 'wrong@email.com');
    await page.fill('[type="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');

    await expect(page.locator('.toast')).toBeVisible({ timeout: 5000 });
  });

  test('should navigate to forgot password', async ({ page }) => {
    await page.goto('http://localhost:8080');
    await page.click('text=Forgot Password');
    await expect(page.locator('h1')).toHaveText(/Forgot|Reset/);
  });
});

test.describe('Student Attendance Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:8080');
    await page.fill('[type="email"]', STUDENT.email);
    await page.fill('[type="password"]', STUDENT.password);
    await page.click('button[type="submit"]');
    await expect(page.locator('.page-title')).toBeVisible({ timeout: 5000 });
  });

  test('should show attendance page', async ({ page }) => {
    await page.click('text=Attendance');
    await expect(page.locator('.page-title')).toHaveText(/Attendance/);
  });

  test('should show QR scanner page', async ({ page }) => {
    await page.click('text=Scan');
    await expect(page.locator('.page-title')).toHaveText(/QR/);
    // Check that camera view or manual input is available
    await expect(page.locator('#qr-manual-input')).toBeVisible();
  });

  test('should navigate to analytics', async ({ page }) => {
    await page.click('text=Analytics');
    await expect(page.locator('.page-title')).toHaveText(/Progress|Analytics/);
  });

  test('should navigate to schedule', async ({ page }) => {
    await page.click('text=Schedule');
    await expect(page.locator('.page-title')).toBeVisible();
  });

  test('should navigate to settings', async ({ page }) => {
    await page.click('text=Settings');
    await expect(page.locator('.page-title')).toHaveText(/Settings/);
  });
});

test.describe('Faculty Session Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:8080');
    await page.fill('[type="email"]', FACULTY.email);
    await page.fill('[type="password"]', FACULTY.password);
    await page.click('button[type="submit"]');
    await expect(page.locator('.page-title')).toBeVisible({ timeout: 5000 });
  });

  test('should show faculty dashboard', async ({ page }) => {
    await expect(page.locator('.page-title')).toHaveText(/Faculty Dashboard/);
  });

  test('should navigate to sessions', async ({ page }) => {
    await page.click('text=Sessions');
    await expect(page.locator('.page-title')).toHaveText(/Sessions/);
  });

  test('should show attendance management', async ({ page }) => {
    await page.click('text=Attendance');
    await expect(page.locator('.page-title')).toHaveText(/Attendance/);
    await expect(page.locator('.data-table')).toBeVisible({ timeout: 5000 });
  });
});

test.describe('Responsive Design', () => {
  test('should render on mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('http://localhost:8080');
    // Login should still work
    await page.fill('[type="email"]', STUDENT.email);
    await page.fill('[type="password"]', STUDENT.password);
    await page.click('button[type="submit"]');
    await expect(page.locator('.page-title')).toBeVisible({ timeout: 5000 });
  });

  test('should render on tablet viewport', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('http://localhost:8080');
    await page.fill('[type="email"]', STUDENT.email);
    await page.fill('[type="password"]', STUDENT.password);
    await page.click('button[type="submit"]');
    await expect(page.locator('.page-title')).toBeVisible({ timeout: 5000 });
  });
});

test.describe('API Health', () => {
  test('backend health endpoint returns ok', async ({ request }) => {
    const resp = await request.get(`${BASE}/health`);
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body.status).toBe('ok');
  });

  test('ML service health endpoint returns ok', async ({ request }) => {
    const resp = await request.get(`http://localhost:8001/health`);
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body.status).toBe('ok');
  });
});