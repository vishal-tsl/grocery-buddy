/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "lh3.googleusercontent.com",
      },
      {
        protocol: "https",
        hostname: "images.basketsavings.com",
      },
      {
        protocol: "https",
        hostname: "images.openfoodfacts.org",
      },
    ],
  },
};

module.exports = nextConfig;
