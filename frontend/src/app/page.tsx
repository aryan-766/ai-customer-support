"use client";

import { useEffect, useState } from "react";
import { KpiCard } from "@/components/KpiCard";
import { PhoneCall, CheckCircle, Clock, AlertTriangle } from "lucide-react";
import Link from "next/link";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface AnalyticsData {
  total_calls: number;
  ai_resolution_rate: number;
  human_transfer_rate: number;
  avg_handle_time_sec: number;
}

interface CallRow {
  call_id: string;
  status: string;
  intent: string | null;
  sentiment: string | null;
  priority: string | null;
  resolved: boolean;
  started_at: string;
}

export default function Dashboard() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [calls, setCalls] = useState<CallRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // In a real app, you'd fetch from http://localhost:8000/analytics/kpis
    // We mock the data here to show the premium UI immediately.
    setTimeout(() => {
      setData({
        total_calls: 1248,
        ai_resolution_rate: 0.76,
        human_transfer_rate: 0.24,
        avg_handle_time_sec: 142.5,
      });
      setCalls([
        { call_id: "c1", status: "completed", intent: "product_support", sentiment: "neutral", priority: "low", resolved: true, started_at: new Date().toISOString() },
        { call_id: "c2", status: "escalated", intent: "complaint", sentiment: "angry", priority: "high", resolved: false, started_at: new Date(Date.now() - 3600000).toISOString() },
        { call_id: "c3", status: "completed", intent: "warranty", sentiment: "positive", priority: "medium", resolved: true, started_at: new Date(Date.now() - 7200000).toISOString() },
      ]);
      setLoading(false);
    }, 800);
  }, []);

  return (
    <div className="p-8 pb-20">
      <header className="mb-10">
        <motion.h1 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="text-3xl font-bold tracking-tight text-white mb-2"
        >
          Overview
        </motion.h1>
        <motion.p 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="text-slate-400"
        >
          Real-time AI voice support metrics
        </motion.p>
      </header>

      {/* KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
        <KpiCard 
          title="Total Calls (Today)" 
          value={loading ? "-" : data?.total_calls || 0} 
          icon={PhoneCall} 
          trend="12% vs yesterday"
          trendUp={true}
          delay={0.1}
        />
        <KpiCard 
          title="AI Resolution Rate" 
          value={loading ? "-" : `${((data?.ai_resolution_rate || 0) * 100).toFixed(1)}%`} 
          icon={CheckCircle} 
          trend="4.2% vs yesterday"
          trendUp={true}
          delay={0.2}
        />
        <KpiCard 
          title="Avg Handle Time" 
          value={loading ? "-" : `${Math.round((data?.avg_handle_time_sec || 0) / 60)}m ${Math.round((data?.avg_handle_time_sec || 0) % 60)}s`} 
          icon={Clock} 
          trend="15s faster"
          trendUp={true}
          delay={0.3}
        />
        <KpiCard 
          title="Escalation Rate" 
          value={loading ? "-" : `${((data?.human_transfer_rate || 0) * 100).toFixed(1)}%`} 
          icon={AlertTriangle} 
          trend="1.1% vs yesterday"
          trendUp={false}
          delay={0.4}
        />
      </div>

      {/* Recent Calls Table */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5, duration: 0.5 }}
        className="glass-panel rounded-2xl overflow-hidden"
      >
        <div className="p-6 border-b border-white/5 flex justify-between items-center">
          <h2 className="text-xl font-semibold text-white">Recent Calls</h2>
          <Link href="/calls" className="text-sm text-blue-400 hover:text-blue-300 transition-smooth">
            View all →
          </Link>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-white/5 text-slate-400">
              <tr>
                <th className="px-6 py-4 font-medium">Call ID</th>
                <th className="px-6 py-4 font-medium">Intent</th>
                <th className="px-6 py-4 font-medium">Sentiment</th>
                <th className="px-6 py-4 font-medium">Status</th>
                <th className="px-6 py-4 font-medium text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-slate-500">Loading calls...</td>
                </tr>
              ) : (
                calls.map((call) => (
                  <tr key={call.call_id} className="hover:bg-white/[0.02] transition-smooth group">
                    <td className="px-6 py-4 font-mono text-slate-300">{call.call_id.substring(0, 8)}...</td>
                    <td className="px-6 py-4 text-slate-300 capitalize">{call.intent?.replace("_", " ") || "Unknown"}</td>
                    <td className="px-6 py-4">
                      <span className={cn(
                        "px-2.5 py-1 rounded-full text-xs font-medium capitalize",
                        call.sentiment === "positive" ? "bg-emerald-500/10 text-emerald-400" :
                        call.sentiment === "angry" ? "bg-rose-500/10 text-rose-400" :
                        "bg-slate-500/10 text-slate-400"
                      )}>
                        {call.sentiment || "Neutral"}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={cn(
                        "px-2.5 py-1 rounded-full text-xs font-medium capitalize",
                        call.resolved ? "bg-blue-500/10 text-blue-400 border border-blue-500/20" : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                      )}>
                        {call.resolved ? "Resolved" : "Escalated"}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Link 
                        href={`/calls/${call.call_id}`}
                        className="text-blue-400 hover:text-blue-300 opacity-0 group-hover:opacity-100 transition-smooth font-medium"
                      >
                        View Details
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </motion.div>
    </div>
  );
}
