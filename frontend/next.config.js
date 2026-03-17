/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "img.basketsavings.com" },
      { protocol: "https", hostname: "images.basketsavings.com" },
    ],
  },
  // Avoid stale chunk errors (e.g. Cannot find module './626.js') when dev server
  // runs from OneDrive/synced folders; remove once stable.
  webpack: (config, { dev }) => {
    if (dev) config.cache = false;
    return config;
  },
};

module.exports = nextConfig;
