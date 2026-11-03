import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Fight Royale",
  description: "Anime cel-shaded arena fighter: duels, online co-op survival and PvP in the browser.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
