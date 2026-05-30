import type { NextConfig } from "next";

const nextConfig: NextConfig = {
    output: 'standalone',
    reactStrictMode: false,

    async rewrites() {
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "localhost:8000";
        const protocol = backendUrl.includes("localhost") ? "http" : "https";
        return [{
            source: "/api/:path*",
            destination: `${protocol}://${backendUrl}/:path*`,
        }];
    }
};

export default nextConfig;
