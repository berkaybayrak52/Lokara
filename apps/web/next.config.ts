import type { NextConfig } from 'next';

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
        destination: 'http://127.0.0.1:3001/:path*',
      },
    ];
  },
};

export default nextConfig;
