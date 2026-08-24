import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { Toaster } from "@/components/ui/toast";

const ibmPlexMono = localFont({
  src: [
    { path: "../assets/fonts/ibm-plex-mono/IBMPlexMono-Regular.woff2", weight: "400", style: "normal" },
    { path: "../assets/fonts/ibm-plex-mono/IBMPlexMono-Medium.woff2", weight: "500", style: "normal" },
    { path: "../assets/fonts/ibm-plex-mono/IBMPlexMono-SemiBold.woff2", weight: "600", style: "normal" },
    { path: "../assets/fonts/ibm-plex-mono/IBMPlexMono-Bold.woff2", weight: "700", style: "normal" },
  ],
  display: "swap",
  variable: "--font-ibm-plex-mono",
});

export const metadata: Metadata = {
  title: {
    default: "PlayStudy",
    template: "%s | PlayStudy",
  },
  applicationName: "PlayStudy",
  description: "A class-centered learning platform for teachers and students.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${ibmPlexMono.variable} h-full antialiased font-mono`}>
      <body className="min-h-full flex flex-col">
        {children}
        <Toaster />
      </body>
    </html>
  );
}
