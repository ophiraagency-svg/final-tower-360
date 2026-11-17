import type { Metadata, Viewport } from "next";
import { Jost, Open_Sans } from "next/font/google";
import { Analytics } from "@vercel/analytics/next";
import "./globals.css";

const jost = Jost({ subsets: ["latin"], weight: ["200", "300", "400"], variable: "--f-display" });
const open = Open_Sans({ subsets: ["latin"], weight: ["300", "400", "600"], variable: "--f-text" });

export const metadata: Metadata = {
  title: "The Final Tower · 360° concept",
  description: "Turn the tower, pick a level, walk the residence. An interactive sales concept by Ophira.",
  metadataBase: new URL("https://final-tower-360.vercel.app"),
  robots: { index: false, follow: false },
  openGraph: { title: "The Final Tower · 360°", description: "Turn the tower, pick a level, walk the residence.", images: [{ url: "/og.jpg", width: 1200, height: 630 }] },
  twitter: { card: "summary_large_image", images: ["/og.jpg"] },
};
export const viewport: Viewport = { themeColor: "#0d1117", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${jost.variable} ${open.variable}`}>
      <body>
        {children}
        <Analytics />
      </body>
    </html>
  );
}
