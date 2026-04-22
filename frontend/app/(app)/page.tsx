"use client";

import Link from "next/link";
import { FileText, MessageSquare } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useDocs } from "@/lib/hooks/use-docs";
import { useAuth } from "@/components/auth/auth-provider";

export default function DashboardPage() {
  const { credentials } = useAuth();
  const { data } = useDocs();

  const activeDocs = data?.documents?.filter((d) => d.status === "active").length ?? 0;
  const totalChunks = data?.total_chunks ?? 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Welcome, {credentials?.tenantId}</h1>
        <p className="text-muted-foreground text-sm mt-1">Your knowledge base at a glance</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Active Documents</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{activeDocs}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Chunks Indexed</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{totalChunks.toLocaleString()}</p>
          </CardContent>
        </Card>
      </div>

      <div className="flex gap-3">
        <Button asChild>
          <Link href="/docs">
            <FileText className="h-4 w-4 mr-2" /> Manage Documents
          </Link>
        </Button>
        <Button variant="secondary" asChild>
          <Link href="/query">
            <MessageSquare className="h-4 w-4 mr-2" /> Ask a Question
          </Link>
        </Button>
      </div>
    </div>
  );
}
