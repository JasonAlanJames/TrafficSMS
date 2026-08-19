import type { Metadata } from "next";
import type { ReactNode } from "react";

import AuthProvider from "../components/auth/AuthProvider";
import AppNav from "../components/navigation/AppNav";
import StructuredData from "../components/StructuredData";
import Footer from "../components/Footer";

import { defaultMetadata } from "../lib/metadata";

import "./globals.css";

export const metadata: Metadata = defaultMetadata;

export default function Layout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <html lang="en">
      <body
        style={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <AuthProvider>
          <main
            className="wrap"
            style={{
              flex: 1,
            }}
          >
            <AppNav />
            {children}
          </main>

          <Footer />
        </AuthProvider>
      </body>
    </html>
  );
}