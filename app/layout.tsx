import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tech Hotspot Daily",
  description: "Curated tech & AI news for IT professionals — updated daily",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
