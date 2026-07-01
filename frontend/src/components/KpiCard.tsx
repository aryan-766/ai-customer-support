"use client";

import { motion } from "framer-motion";
import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface KpiCardProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
  trend?: string;
  trendUp?: boolean;
  delay?: number;
}

export function KpiCard({ title, value, icon: Icon, trend, trendUp, delay = 0 }: KpiCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay, ease: [0.22, 1, 0.36, 1] }}
      className="glass-panel p-6 rounded-2xl relative overflow-hidden group"
    >
      {/* Hover gradient effect */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-500/0 to-purple-500/0 group-hover:from-blue-500/5 group-hover:to-purple-500/5 transition-smooth duration-500" />
      
      <div className="relative z-10 flex justify-between items-start">
        <div>
          <p className="text-sm font-medium text-slate-400 mb-1">{title}</p>
          <h3 className="text-3xl font-bold tracking-tight text-white">{value}</h3>
          
          {trend && (
            <p className={cn(
              "text-xs font-medium mt-2 flex items-center",
              trendUp ? "text-emerald-400" : "text-rose-400"
            )}>
              {trendUp ? "↑" : "↓"} {trend}
            </p>
          )}
        </div>
        
        <div className="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center border border-white/10 group-hover:bg-blue-500/10 group-hover:border-blue-500/30 transition-smooth">
          <Icon className="w-6 h-6 text-slate-300 group-hover:text-blue-400 transition-smooth" />
        </div>
      </div>
    </motion.div>
  );
}
