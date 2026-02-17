import { test, expect } from '@playwright/test';

function uniqueEmail(prefix = 'e2e') {
  return `${prefix}_${Date.now()}_${Math.floor(Math.random() * 1e9)}@example.com`;
}

async function registerUser(request, namePrefix) {
  const email = uniqueEmail(namePrefix);
  const password = 'Password123!';
  const res = await request.post('/api/auth/register', {
    data: {
      email,
      password,
      name: `${namePrefix} User`,
      organization: 'E2E',
    },
  });
  expect(res.ok()).toBeTruthy();
  const body = await res.json();
  expect(body.access_token).toBeTruthy();
  return {
    email,
    token: body.access_token,
    headers: { Authorization: `Bearer ${body.access_token}` },
  };
}

test('User isolation: reports and pending trades are isolated by account', async ({ request }) => {
  const userA = await registerUser(request, 'userA');
  const userB = await registerUser(request, 'userB');

  // User A creates a report.
  const saveRes = await request.post('/api/reports', {
    headers: userA.headers,
    data: {
      session_id: `dd_isolation_${Date.now()}`,
      project_name: 'Isolation Report A',
      company_name: 'Tenant A Co',
      analysis_type: 'due-diligence',
      steps: [],
      status: 'completed',
    },
  });
  expect(saveRes.ok()).toBeTruthy();
  const saveBody = await saveRes.json();
  const reportId = saveBody.report_id;
  expect(reportId).toBeTruthy();

  // A can see its own report.
  const reportsARes = await request.get('/api/reports', { headers: userA.headers });
  expect(reportsARes.ok()).toBeTruthy();
  const reportsABody = await reportsARes.json();
  expect(reportsABody.reports.some((r) => r.id === reportId)).toBeTruthy();

  // B cannot see A's report and cannot access report detail.
  const reportsBRes = await request.get('/api/reports', { headers: userB.headers });
  expect(reportsBRes.ok()).toBeTruthy();
  const reportsBBody = await reportsBRes.json();
  expect(reportsBBody.reports.some((r) => r.id === reportId)).toBeFalsy();

  const reportDetailBRes = await request.get(`/api/reports/${reportId}`, { headers: userB.headers });
  expect(reportDetailBRes.status()).toBe(404);

  // A creates one pending trade via mock hook.
  const pendingCreateARes = await request.post(
    '/api/trading/mock/create-pending?symbol=BTC-USDT-SWAP&direction=long&leverage=2&amount_percent=0.2&tp_percent=1.0&sl_percent=1.0',
    { headers: userA.headers },
  );
  expect(pendingCreateARes.ok()).toBeTruthy();
  const pendingCreateABody = await pendingCreateARes.json();
  expect(pendingCreateABody.success).toBeTruthy();

  // Pending trades must be tenant-scoped.
  const pendingARes = await request.get('/api/trading/pending', { headers: userA.headers });
  expect(pendingARes.ok()).toBeTruthy();
  const pendingABody = await pendingARes.json();
  expect(pendingABody.count).toBeGreaterThan(0);

  const pendingBRes = await request.get('/api/trading/pending', { headers: userB.headers });
  expect(pendingBRes.ok()).toBeTruthy();
  const pendingBBody = await pendingBRes.json();
  expect(pendingBBody.count).toBe(0);
});
