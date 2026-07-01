"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, PhoneCall, Settings, HeadphonesIcon } from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Live Calls", href: "/calls", icon: PhoneCall },
  { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 glass-panel border-r border-white/5 flex flex-col h-full flex-shrink-0">
      <div className="h-16 flex items-center px-6 border-b border-white/5">
        <HeadphonesIcon className="w-6 h-6 text-blue-500 mr-3" />
        <span className="font-semibold text-lg tracking-tight text-white">Ambrane AI</span>
      </div>

      <nav className="flex-1 px-4 py-6 space-y-2">
        {navItems.map((item) => {
          const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center px-3 py-2.5 rounded-lg text-sm font-medium transition-smooth group relative overflow-hidden",
                isActive
                  ? "text-white bg-blue-500/10 border border-blue-500/20"
                  : "text-slate-400 hover:text-white hover:bg-white/5"
              )}
            >
              <item.icon
                className={cn(
                  "w-5 h-5 mr-3 transition-smooth",
                  isActive ? "text-blue-500" : "text-slate-500 group-hover:text-slate-300"
                )}
              />
              {item.name}
              
              {isActive && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-blue-500 rounded-r-full" />
              )}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-white/5">
        <div className="flex items-center px-3 py-2">
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-500 to-purple-500 flex items-center justify-center text-sm font-bold text-white shadow-lg shadow-blue-500/20">
            A
          </div>
          <div className="ml-3">
            <p className="text-sm font-medium text-white">Agent Alpha</p>
            <p className="text-xs text-slate-500">Active</p>
          </div>
          <div className="ml-auto w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
        </div>
      </div>
    </aside>
  );
}
