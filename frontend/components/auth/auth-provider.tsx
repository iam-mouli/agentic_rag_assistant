"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { clearCredentials, getCredentials, setCredentials } from "@/lib/auth";
import type { Credentials } from "@/lib/types";

interface AuthCtx {
  credentials: Credentials | null;
  login: (creds: Credentials) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthCtx>({
  credentials: null,
  login: () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [credentials, setCredsState] = useState<Credentials | null>(null);

  useEffect(() => {
    setCredsState(getCredentials());
  }, []);

  const login = useCallback((creds: Credentials) => {
    setCredentials(creds);
    setCredsState(creds);
  }, []);

  const logout = useCallback(() => {
    clearCredentials();
    setCredsState(null);
  }, []);

  return (
    <AuthContext.Provider value={{ credentials, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
