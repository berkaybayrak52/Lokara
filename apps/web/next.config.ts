import type { NextConfig } from 'next';

function apiBackendUrl(): string {
  const configured = process.env.API_BACKEND_URL?.replace(/\/$/, '');
  if (configured) return configured;
  if (process.env.VERCEL === '1') {
    throw new Error('API_BACKEND_URL is required for a Vercel deployment');
  }
  return 'http://127.0.0.1:3001';
}

const nextConfig: NextConfig = {
  // Workspace packages ship TS source; Next transpiles them.
  transpilePackages: ['@lokara/ui'],
  // The dev-only overlay badge defaults to bottom-LEFT, where it sits directly
  // on top of the sidebar's account block. The pitch runs on `bun dev`, so it
  // is visible in the demo — move it out of the way.
  devIndicators: { position: 'bottom-right' },
  async rewrites() {
    return [
      {
        source: '/api/backend/:path*',
        destination: `${apiBackendUrl()}/:path*`,
      },
    ];
  },
};

export default nextConfig;
