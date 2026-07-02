import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Jarvis",
  description: "Your personal AI assistant",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-jarvis-bg text-jarvis-text antialiased">{children}</body>
    </html>
  );
}
