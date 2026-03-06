/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "img.basketsavings.com" },
      { protocol: "https", hostname: "images.basketsavings.com" },
    ],
  },
};

module.exports = nextConfig;
