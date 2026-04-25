"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { FileText, MessageSquare, ScrollText, Settings, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/components/auth/auth-provider";

const navItems = [
  { href: "/", label: "Dashboard", icon: Zap },
  { href: "/docs", label: "Documents", icon: FileText },
  { href: "/query", label: "Query", icon: MessageSquare },
  { href: "/logs", label: "Logs", icon: ScrollText },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function AppNav() {
  const pathname = usePathname();
  const { credentials } = useAuth();

  return (
    <header className="sticky top-0 z-50 border-b bg-background">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
        <div className="flex items-center gap-2">
          <Zap className="h-5 w-5 text-primary" />
          <span className="font-semibold text-sm">RAG Platform</span>
          {credentials && (
            <span className="ml-2 rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
              {credentials.tenantId}
            </span>
          )}
        </div>
        <nav className="flex items-center gap-1">
          {navItems.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                href === "/" ? pathname === "/" : pathname.startsWith(href)
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
