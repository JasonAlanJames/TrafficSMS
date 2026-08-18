import type { Metadata } from 'next';
import type { ReactNode } from 'react';

import AuthProvider from '../components/auth/AuthProvider';
import AppNav from '../components/navigation/AppNav';
import './globals.css';

export const metadata: Metadata = {
  title: 'TrafficSMS',
  description: 'Localized traffic intelligence by SMS',
};

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <main className="wrap">
            <AppNav />
            {children}
          </main>
        </AuthProvider>
      </body>
    </html>
  );
}
