import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Technical Doc Generator',
  description: 'AI-powered technical document generation with Context7 and Bedrock',
  keywords: ['documentation', 'AI', 'SRS', 'API docs', 'architecture'],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
      </head>
      <body>
        <div id="app-root">
          {children}
        </div>
      </body>
    </html>
  );
}
