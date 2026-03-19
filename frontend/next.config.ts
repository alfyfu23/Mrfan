import type { NextConfig } from "next";

const nextConfig: NextConfig = {
    /* config options here */
    output: 'standalone',

    reactStrictMode: false, /* @note: To prevent duplicated call of useEffect */
    // swcMinify: true,

    async rewrites() {
        return [{
            source: "/api/:path*",
            destination: "https://backend-mrfan.app.secoder.net/:path*",
        }];
    }
};

export default nextConfig;
