"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "./auth-provider";

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { credentials } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (credentials === null) {
      router.replace("/login");
    }
  }, [credentials, router]);

  if (!credentials) return null;
  return <>{children}</>;
}
