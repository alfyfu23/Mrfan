import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { UserContextProvider } from "@/context/UserContext";
import { ToastContainer } from "react-toastify";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
    title: "Chatting Room",
    description: "Created by team MrFan",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en">
            <body className={inter.className}>
                <UserContextProvider>
                    {children}
                    <ToastContainer
                        position="top-right"
                        autoClose={3000}
                        hideProgressBar={false}
                        pauseOnHover
                        draggable
                        style={{ zIndex: 9999 }}
                    />
                </UserContextProvider>
            </body>
        </html>
    );
}