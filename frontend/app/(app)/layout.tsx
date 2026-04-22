import { ProtectedRoute } from "@/components/auth/protected-route";
import { AppNav } from "@/components/nav/app-nav";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute>
      <div className="min-h-screen flex flex-col">
        <AppNav />
        <main className="flex-1 mx-auto w-full max-w-7xl px-4 py-8">
          {children}
        </main>
      </div>
    </ProtectedRoute>
  );
}
