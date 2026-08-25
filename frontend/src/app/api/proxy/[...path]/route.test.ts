/** @jest-environment node */

import { NextRequest } from 'next/server';

import { GET, POST } from './route';


describe('BFF proxy boundary', () => {
  const originalBackendUrl = process.env.BACKEND_API_URL;

  afterEach(() => {
    process.env.BACKEND_API_URL = originalBackendUrl;
    jest.restoreAllMocks();
  });

  test('forwards path/query and converts the HttpOnly token to authorization', async () => {
    process.env.BACKEND_API_URL = 'https://backend.example.test';
    const backendFetch = jest.spyOn(global, 'fetch').mockImplementation(async (input) => {
      const request = input as Request;
      expect(request.url).toBe('https://backend.example.test/exams?size=10');
      expect(request.headers.get('authorization')).toBe('Bearer cookie-token');
      expect(request.headers.has('host')).toBe(false);
      return new Response(JSON.stringify({ items: [] }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      });
    });
    const request = new NextRequest('http://frontend.test/api/proxy/exams?size=10', {
      headers: {
        authorization: 'Bearer browser-controlled-token',
        cookie: 'access_token=cookie-token; browser_secret=do-not-forward',
        origin: 'http://frontend.test',
      },
    });

    const response = await GET(request);

    expect(backendFetch).toHaveBeenCalledTimes(1);
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({ items: [] });
  });

  test('rejects cross-origin mutations before contacting the backend', async () => {
    const backendFetch = jest.spyOn(global, 'fetch');
    const request = new NextRequest('http://frontend.test/api/proxy/exams', {
      method: 'POST',
      body: JSON.stringify({ title: 'Blocked' }),
      headers: {
        'content-type': 'application/json',
        cookie: 'csrf_token=csrf-token',
        origin: 'https://attacker.example',
        'x-csrf-token': 'csrf-token',
      },
    });

    const response = await POST(request);

    expect(response.status).toBe(403);
    await expect(response.json()).resolves.toEqual(
      expect.objectContaining({ error_code: 'ORIGIN_NOT_ALLOWED' }),
    );
    expect(backendFetch).not.toHaveBeenCalled();
  });

  test('accepts same-origin mutations and strips browser credentials', async () => {
    process.env.BACKEND_API_URL = 'https://backend.example.test';
    const backendFetch = jest.spyOn(global, 'fetch').mockImplementation(async (input) => {
      const backendRequest = input as Request;
      expect(backendRequest.headers.get('authorization')).toBe('Bearer trusted-access');
      expect(backendRequest.headers.has('cookie')).toBe(false);
      expect(backendRequest.headers.has('origin')).toBe(false);
      expect(backendRequest.headers.has('referer')).toBe(false);
      expect(backendRequest.headers.has('forwarded')).toBe(false);
      expect(backendRequest.headers.has('x-forwarded-for')).toBe(false);
      expect(backendRequest.headers.has('x-real-ip')).toBe(false);
      expect(backendRequest.headers.has('x-csrf-token')).toBe(false);
      return new Response(JSON.stringify({ id: 'exam-1' }), {
        status: 201,
        headers: { 'content-type': 'application/json' },
      });
    });
    const request = new NextRequest('http://frontend.test/api/proxy/exams', {
      method: 'POST',
      body: JSON.stringify({ title: 'Allowed' }),
      headers: {
        authorization: 'Bearer hostile-access',
        'content-type': 'application/json',
        cookie: 'access_token=trusted-access; csrf_token=csrf-token; hostile=secret',
        origin: 'http://frontend.test',
        referer: 'http://frontend.test/dashboard',
        forwarded: 'for=203.0.113.10;proto=https',
        'x-forwarded-for': '203.0.113.10',
        'x-real-ip': '203.0.113.10',
        'x-csrf-token': 'csrf-token',
      },
    });

    const response = await POST(request);

    expect(response.status).toBe(201);
    expect(backendFetch).toHaveBeenCalledTimes(1);
  });

  test('rewrites backend redirects to the BFF origin', async () => {
    process.env.BACKEND_API_URL = 'https://backend.example.test';
    jest.spyOn(global, 'fetch').mockResolvedValue(
      new Response(null, {
        status: 307,
        headers: { location: 'https://backend.example.test/exams' },
      }),
    );
    const request = new NextRequest('http://frontend.test/api/proxy/exams/');

    const response = await GET(request);

    expect(response.status).toBe(307);
    expect(response.headers.get('location')).toBe('/api/proxy/exams');
  });

  test('preserves private download bytes and content headers', async () => {
    process.env.BACKEND_API_URL = 'https://backend.example.test';
    const fileBytes = new Uint8Array([0, 37, 80, 68, 70, 255]);
    const backendFetch = jest.spyOn(global, 'fetch').mockResolvedValue(
      new Response(fileBytes, {
        status: 200,
        headers: {
          'content-type': 'application/pdf',
          'content-disposition': 'attachment; filename="lesson.pdf"',
        },
      }),
    );
    const request = new NextRequest(
      'http://frontend.test/api/proxy/materials/00000000-0000-0000-0000-000000000001/download',
      { headers: { cookie: 'access_token=cookie-token' } },
    );

    const response = await GET(request);

    expect(backendFetch).toHaveBeenCalledTimes(1);
    const backendRequest = backendFetch.mock.calls[0][0] as Request;
    expect(backendRequest.headers.get('authorization')).toBe(
      'Bearer cookie-token',
    );
    expect(response.status).toBe(200);
    expect(response.headers.get('content-type')).toBe('application/pdf');
    expect(response.headers.get('content-disposition')).toBe(
      'attachment; filename="lesson.pdf"',
    );
    expect(new Uint8Array(await response.arrayBuffer())).toEqual(fileBytes);
  });

  test('creates a canonical correlated envelope for BFF-owned failures', async () => {
    process.env.BACKEND_API_URL = 'https://backend.example.test';
    jest
      .spyOn(global, 'fetch')
      .mockRejectedValue(new Error('canary upstream credential'));
    const consoleError = jest
      .spyOn(console, 'error')
      .mockImplementation(() => undefined);
    const requestId = '8f37b4ca-2014-4cec-aa2d-3f967c27eb8e';
    const request = new NextRequest('http://frontend.test/api/proxy/exams', {
      headers: { 'X-Request-ID': requestId },
    });

    const response = await GET(request);

    expect(response.status).toBe(500);
    expect(response.headers.get('X-Request-ID')).toBe(requestId);
    await expect(response.json()).resolves.toEqual({
      error_code: 'PROXY_ERROR',
      details: {},
      request_id: requestId,
    });
    expect(consoleError).toHaveBeenCalledWith(
      `Proxy request failed request_id=${requestId}`,
    );
    expect(JSON.stringify(consoleError.mock.calls)).not.toContain('canary');
  });
});
