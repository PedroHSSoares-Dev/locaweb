import { expect, test } from '@playwright/test';

const session = {
  email: 'pedrohssoares@live.com',
  token: 'e2e-session-token',
  expiresAt: Math.floor(Date.now() / 1000) + 3600,
  role: 'admin',
  permissions: ['chat:use', 'users:read', 'users:write', 'usage:read'],
  isOwner: true,
};

async function mockApi(page) {
  await page.addInitScript((value) => {
    window.sessionStorage.setItem('predictfy_chat_session', JSON.stringify(value));
    window.localStorage.setItem(`predictfy_chat_panel:${value.email}:open`, 'false');
  }, session);

  await page.route('**/api/**', async (route) => {
    const path = new URL(route.request().url()).pathname;
    let body = { disponivel: false, mensagem: 'Fixture de interface' };
    if (path.endsWith('/chat/session')) {
      body = { ...session, expires_at: session.expiresAt, is_owner: true };
    } else if (path.endsWith('/chat/status')) {
      body = { available: true, provider: 'openai', model: 'gpt-5.6-luna' };
    } else if (path.endsWith('/kpi')) {
      body = {
        disponivel: true,
        P2: { violacoesAno: 42, metaAnual: 37.5, metaMin: 36, metaMax: 39, pctUtilizado: 112, margemRestante: -4.5, olaHoras: 4, tendencia: 'critico' },
        P3: { violacoesAno: 196, metaAnual: 247, metaMin: 231, metaMax: 263, pctUtilizado: 79.4, margemRestante: 51, olaHoras: 12, tendencia: 'dentro_meta' },
      };
    } else if (path.endsWith('/previsoes/d1')) {
      body = { disponivel: true, total: 44, p2: 8, p3: 36, modelo_usado: 'baseline_sazonal_7d', mae: 12.7, reconciliado: false };
    } else if (path.endsWith('/previsoes/d7')) {
      body = { disponivel: true, total: 40, p2: 9, p3: 31, modelo_usado: 'baseline_sazonal_7d', mae: 12.19, reconciliado: true };
    } else if (path.includes('/chat/conversations')) {
      body = path.endsWith('/conversations') ? { conversations: [] } : { messages: [], dashboard_context: { route: '/gestao', label: 'GESTÃO', filters: {} } };
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  });
}

test('mobile dashboard keeps full width after chat and route transition', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockApi(page);
  await page.goto('/gestao');

  await expect(page.getByRole('heading', { name: 'Centro de Gestão' })).toBeVisible();
  const trigger = page.getByRole('button', { name: 'Abrir navegação' });
  const triggerBox = await trigger.boundingBox();
  expect(triggerBox.width).toBeGreaterThanOrEqual(44);
  expect(triggerBox.height).toBeGreaterThanOrEqual(44);

  await page.getByRole('button', { name: 'Abrir assistente Predictfy' }).click();
  await expect(page.getByRole('dialog', { name: 'Predictfy Agent' })).toBeVisible();
  await page.getByRole('button', { name: 'Recolher assistente' }).click();

  await trigger.click();
  await page.getByRole('link', { name: 'MONITORAMENTO' }).click();
  await expect(page.getByRole('heading', { name: 'Monitoramento Preditivo' })).toBeVisible();

  const pageBox = await page.getByRole('main').boundingBox();
  expect(pageBox.width).toBeGreaterThanOrEqual(380);
  const dimensions = await page.evaluate(() => ({
    viewport: window.innerWidth,
    root: document.documentElement.scrollWidth,
    main: document.querySelector('.app-main')?.getBoundingClientRect().width,
  }));
  expect(dimensions.main).toBeGreaterThanOrEqual(380);
  expect(dimensions.root).toBeLessThanOrEqual(dimensions.viewport);
});

test('login guides FIAP evaluators to use their institutional email', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto('/gestao');

  const evaluatorNote = page.getByLabel('Orientação para professores avaliadores');
  await expect(evaluatorNote).toBeVisible();
  await expect(evaluatorNote).toContainText('Professor(a) avaliador(a)?');
  await expect(evaluatorNote).toContainText('e-mail institucional da FIAP');
});

test('compact sidebar hides KPI label and Luna status stays inside its badge', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page);
  await page.goto('/gestao');
  // Chromium starts at (0, 0) in some CI runners, which is inside the sidebar
  // and legitimately activates its hover expansion before the first assertion.
  await page.mouse.move(1200, 800);

  const sidebar = page.locator('.sidebar');
  const kpiLabel = page.locator('.sidebar-kpi small');
  await expect(sidebar).toHaveCSS('width', '60px');
  await expect(kpiLabel).toHaveCSS('opacity', '0');

  await sidebar.hover();
  await expect(kpiLabel).toHaveCSS('opacity', '1');
  await expect(page.getByRole('link', { name: 'MODELOS' })).toHaveCount(0);

  await page.getByRole('button', { name: 'Abrir assistente Predictfy' }).click();
  const provider = page.getByRole('button', { name: 'Assistente online' });
  await expect(provider).toBeVisible();
  await expect(provider).toContainText('LUNA ONLINE');

  await expect.poll(() => provider.evaluate((element) => element.clientWidth)).toBeGreaterThan(70);
  const bounds = await provider.evaluate((element) => ({
    clientWidth: element.clientWidth,
    scrollWidth: element.scrollWidth,
    clientHeight: element.clientHeight,
    scrollHeight: element.scrollHeight,
  }));
  expect(bounds.scrollWidth).toBeLessThanOrEqual(bounds.clientWidth + 1);
  expect(bounds.scrollHeight).toBeLessThanOrEqual(bounds.clientHeight + 1);
});

test('technical page omits the predictive risk module from the presentation', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page);
  await page.goto('/tecnico');

  await expect(page.getByRole('heading', { name: 'Investigação Técnica' })).toBeVisible();
  await expect(page.getByText('Triagem preditiva XGBoost')).toHaveCount(0);
  await expect(page.locator('.dashboard-module')).toHaveCount(2);
  await expect(page.locator('.dashboard-module').nth(1)).toContainText('MÓDULO 02');
  await expect(page.locator('.dashboard-module').nth(1)).toContainText('Perfis operacionais K-Means');
});
