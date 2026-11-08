import type { NextConfig } from 'next';

// 하위 경로 배포(GitHub Pages 프로젝트 사이트 등)를 위한 접두사.
// For sub-path deployments (e.g. https://user.github.io/lionsparkofvamos):
//   NEXT_PUBLIC_BASE_PATH=/lionsparkofvamos npm run build
const basePath = process.env.NEXT_PUBLIC_BASE_PATH?.replace(/\/+$/, '') || undefined;

const config: NextConfig = {
    output: 'export',
    ...(basePath ? { basePath, assetPrefix: basePath } : {}),
    turbopack: { root: process.cwd() },
    poweredByHeader: false,
    reactStrictMode: true,
    images: { unoptimized: true },
    ...(process.env.NODE_ENV === 'development'
        ? {
              rewrites: async () => [
                  { source: '/api/:path*', destination: 'http://127.0.0.1:8787/api/:path*' },
              ],
          }
        : {}),
};

export default config;
