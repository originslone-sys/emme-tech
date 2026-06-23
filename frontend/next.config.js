/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.BACKEND_URL}/api/:path*`,
      },
      {
        source: '/files/:path*',
        destination: `${process.env.BACKEND_URL}/files/:path*`,
      },
    ]
  },
}

module.exports = nextConfig
