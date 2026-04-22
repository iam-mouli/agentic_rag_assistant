"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/components/auth/auth-provider";
import { api } from "@/lib/api-client";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [tenantId, setTenantId] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tenantId.trim() || !apiKey.trim()) return;
    setLoading(true);

    // Temporarily store creds so api-client can inject them for the probe
    sessionStorage.setItem(
      "rag_credentials",
      JSON.stringify({ tenantId: tenantId.trim(), apiKey: apiKey.trim() })
    );

    try {
      await api.get(`/${tenantId.trim()}/docs`);
      login({ tenantId: tenantId.trim(), apiKey: apiKey.trim() });
      router.replace("/");
    } catch (err) {
      sessionStorage.removeItem("rag_credentials");
      const msg = (err as Error).message;
      if (msg !== "Unauthorized") toast.error("Invalid tenant ID or API key");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/40 px-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-2">
            <Zap className="h-8 w-8 text-primary" />
          </div>
          <CardTitle>RAG Platform</CardTitle>
          <p className="text-sm text-muted-foreground mt-1">
            Enter your tenant credentials to continue
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1">
              <label className="text-sm font-medium" htmlFor="tenant-id">
                Tenant ID
              </label>
              <Input
                id="tenant-id"
                value={tenantId}
                onChange={(e) => setTenantId(e.target.value)}
                placeholder="e.g. ome"
                autoComplete="username"
                required
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium" htmlFor="api-key">
                API Key
              </label>
              <Input
                id="api-key"
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="Your API key"
                autoComplete="current-password"
                required
              />
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? <Spinner className="mr-2" /> : null}
              Sign in
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
