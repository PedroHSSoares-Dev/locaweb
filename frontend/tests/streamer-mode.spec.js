import { expect, test } from '@playwright/test';

const session = {
  email: 'pedrohssoares@live.com',
  token: 'streamer-mode-session',
  expiresAt: Math.floor(Date.now() / 1000) + 3600,
  role: 'admin',
  permissions: ['chat:use', 'users:read', 'users:write', 'usage:read'],
  isOwner: true,
};

const users = [
  {
    id: 'owner',
    email: 'pedrohssoares@live.com',
    role: 'admin',
    status: 'active',
    is_owner: true,
    created_at: '2026-08-01T12:00:00Z',
    last_login_at: '2026-09-14T10:00:00Z',
  },
  {
    id: 'professor',
    email: 'professor.avaliador@fiap.com.br',
    role: 'member',
    status: 'active',
    created_at: '2026-09-01T12:00:00Z',
    last_login_at: null,
  },
];

async function mockAdmin(page) {
  await page.addInitScript((value) => {
    window.sessionStorage.setItem('predictfy_chat_session', JSON.stringify(value));
    window.localStorage.setItem(`predictfy_chat_panel:${value.email}:open`, 'false');
    if (!window.sessionStorage.getItem('streamer_test_initialized')) {
      window.localStorage.removeItem(`predictfy_streamer_mode:${value.email}`);
      window.sessionStorage.setItem('streamer_test_initialized', 'true');
    }
  }, session);

  await page.route('**/api/**', async (route) => {
    const path = new URL(route.request().url()).pathname;
    let body = { disponivel: false };

    if (path.endsWith('/chat/session')) {
      body = { ...session, expires_at: session.expiresAt, is_owner: true };
    } else if (path.endsWith('/admin/users')) {
      body = { users };
    } else if (path.endsWith('/admin/usage')) {
      body = {
        totals: { total_tokens: 1800, input_tokens: 1200, output_tokens: 600, generated_responses: 2, cache_hits: 0 },
        users: users.map((item, index) => ({ ...item, total_tokens: 900 - (index * 100), input_tokens: 600, output_tokens: 300, generated_responses: 1, cache_hits: 0, saved_tokens: 0 })),
      };
    } else if (path.endsWith('/admin/preflight')) {
      body = { status: 'ready', passed: 1, total: 1, checks: [{ name: 'frontend', ok: true, detail: 'Pronto' }] };
    } else if (path.endsWith('/kpi')) {
      body = { disponivel: true, P2: { tendencia: 'dentro_meta', margemRestante: 1 }, P3: { tendencia: 'dentro_meta', margemRestante: 1 } };
    }

    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
  });
}

test('streamer mode masks admin identities and survives reload', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockAdmin(page);
  await page.goto('/admin');

  await expect(page.getByText('professor.avaliador@fiap.com.br').first()).toBeVisible();

  const sidebar = page.locator('.sidebar');
  await sidebar.hover();
  await page.getByRole('button', { name: 'Ativar modo streamer' }).click();

  await expect(page.getByLabel('Modo streamer ativo')).toBeVisible();
  await expect(page.getByText('professor.avaliador@fiap.com.br')).toHaveCount(0);
  await expect(page.getByText('pedrohssoares@live.com')).toHaveCount(0);
  await expect(page.getByText(/IDENTIDADE #/).first()).toBeVisible();

  await page.reload();
  await expect(page.getByLabel('Modo streamer ativo')).toBeVisible();
  await expect(page.getByText('professor.avaliador@fiap.com.br')).toHaveCount(0);

  await page.getByRole('button', { name: 'DESATIVAR', exact: true }).click();
  await expect(page.getByText('professor.avaliador@fiap.com.br').first()).toBeVisible();
});
