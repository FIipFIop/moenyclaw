/** @type {import('next').NextConfig} */
const nextConfig = {
  // Allow backend API calls from server components during build
  experimental: { serverActions: { allowedOrigins: ["localhost:8000"] } },
  // Suppress image hostname warnings for external sources
  images: { unoptimized: true },
};

export default nextConfig;
