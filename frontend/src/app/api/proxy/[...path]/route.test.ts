/** @jest-environment node */

import { NextRequest } from 'next/server';

import { GET } from './route';


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
      headers: { cookie: 'token=cookie-token' },
    });

    const response = await GET(request);

    expect(backendFetch).toHaveBeenCalledTimes(1);
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({ items: [] });
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
});
