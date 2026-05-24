import Link from 'next/link'

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <h1 className="text-4xl font-bold mb-4">Video-Generate</h1>
      <p className="text-lg text-gray-600 mb-8">
        AI-powered video generation platform
      </p>
      <div className="flex gap-4">
        <Link
          href="/dashboard"
          className="rounded-lg bg-blue-600 px-6 py-3 text-white hover:bg-blue-700"
        >
          Go to Dashboard
        </Link>
        <Link
          href="/create"
          className="rounded-lg border border-gray-300 px-6 py-3 text-gray-700 hover:bg-gray-100"
        >
          Create Video
        </Link>
      </div>
    </main>
  )
}
