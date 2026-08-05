import type { NextConfig } from "next";
import { getBackendUrl } from "./src/lib/backend-url";

const backendUrl = new URL(getBackendUrl());

const nextConfig: NextConfig = {
  /* config options here */
  reactCompiler: true,
  images: {
    remotePatterns: [
      {
        protocol: backendUrl.protocol.slice(0, -1) as "http" | "https",
        hostname: backendUrl.hostname,
        port: backendUrl.port,
        pathname: '/uploads/**',
      },
    ],
  },
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-DNS-Prefetch-Control',
            value: 'on'
          },
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=63072000; includeSubDomains; preload'
          },
          {
            key: 'X-Frame-Options',
            value: 'SAMEORIGIN'
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff'
          },
          {
            key: 'Referrer-Policy',
            value: 'origin-when-cross-origin'
          },
          {
            key: 'Content-Security-Policy',
            value: "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' blob: data: http://127.0.0.1:8000 https://*; font-src 'self' data: https://fonts.gstatic.com; connect-src 'self' http://127.0.0.1:8000 https://openrouter.ai;"
          }
        ]
      }
    ];
  },
  async rewrites() {
    return [
      {
        source: '/uploads/:path*',
        destination: `${backendUrl.origin}/uploads/:path*`,
      },
    ];
  },
};

export default nextConfig;
