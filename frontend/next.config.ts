import type { NextConfig } from "next";
import { getBackendUrl } from "./src/lib/backend-url";
import { createContentSecurityPolicy } from "./src/lib/content-security-policy";

const backendUrl = new URL(getBackendUrl());
const contentSecurityPolicy = createContentSecurityPolicy(
  process.env.NODE_ENV === 'development',
);

const nextConfig: NextConfig = {
  /* config options here */
  distDir: process.env.NEXT_DIST_DIR ?? '.next',
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
            value: contentSecurityPolicy,
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
