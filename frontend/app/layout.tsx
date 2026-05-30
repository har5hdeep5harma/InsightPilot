import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "InsightPilot",
  description: "Premium AI-assisted data analysis studio for evidence-backed reports."
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
