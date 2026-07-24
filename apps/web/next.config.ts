import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // Workspace packages ship TS source; Next transpiles them.
  transpilePackages: ['@lokara/ui'],
};

export default nextConfig;
