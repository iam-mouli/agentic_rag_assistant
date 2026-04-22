"use client";

import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/components/auth/auth-provider";

export default function SettingsPage() {
  const { credentials, logout } = useAuth();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.replace("/login");
  };

  return (
    <div className="space-y-6 max-w-xl">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-muted-foreground text-sm mt-1">Tenant information and session management</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Tenant Info</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Tenant ID</span>
            <span className="font-mono font-medium">{credentials?.tenantId}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">API Key</span>
            <span className="font-mono">{"•".repeat(16)}</span>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Key Rotation</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            API key rotation is an admin operation. Contact your platform administrator or run:
          </p>
          <pre className="mt-2 rounded bg-muted px-3 py-2 text-xs overflow-x-auto">
            {`curl -X POST http://localhost:8000/tenants/${credentials?.tenantId}/rotate-key \\
  -H "X-Platform-Admin-Key: <admin-key>"`}
          </pre>
        </CardContent>
      </Card>

      <div>
        <Button variant="destructive" onClick={handleLogout}>
          <LogOut className="h-4 w-4 mr-2" /> Sign out
        </Button>
      </div>
    </div>
  );
}
