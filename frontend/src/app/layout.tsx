import type { Metadata } from 'next'
import './globals.css'
import ClientLayout from './ClientLayout'

export const metadata: Metadata = {
  title: 'Video-Generate',
  description: 'AI-powered video generation platform for e-commerce product videos',
  keywords: ['video generation', 'AI video', 'e-commerce', 'product video'],
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-slate-900 text-slate-100 antialiased">
        <ClientLayout>{children}</ClientLayout>
      </body>
    </html>
  )
}
