"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PhoneCall, CheckCircle, Clock, AlertTriangle, ArrowLeft } from "lucide-react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface CallRow {
  call_id: string;
  status: string;
  intent: string | null;
  sentiment: string | null;
  priority: string | null;
  resolved: boolean;
  started_at: string;
}

export default function CallsPage() {
  const [calls, setCalls] = useState<CallRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchCalls() {
      try {
        const res = await fetch("http://localhost:8000/api/v1/calls");
        if (!res.ok) {
          throw new Error("Failed to fetch calls from backend");
        }
        const data = await res.json();
        setCalls(data.calls || []);
        setError(null);
      } catch (err: any) {
        console.error("Error fetching calls:", err);
        setError(err.message || "Failed to load calls");
        // Fallback mock data if backend connection fails so UI is still inspectable
        setCalls([
          { call_id: "c-1", status: "completed", intent: "product_support", sentiment: "neutral", priority: "low", resolved: true, started_at: new Date().toISOString() },
          { call_id: "c-2", status: "escalated", intent: "complaint", sentiment: "angry", priority: "high", resolved: false, started_at: new Date(Date.now() - 3600000).toISOString() },
          { call_id: "c-3", status: "completed", intent: "warranty", sentiment: "positive", priority: "medium", resolved: true, started_at: new Date(Date.now() - 7200000).toISOString() },
        ]);
      } finally {
        setLoading(false);
      }
    }

    fetchCalls();
    
    // Poll every 5 seconds for new live calls
    const interval = setInterval(fetchCalls, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="p-8 pb-20 max-w-7xl mx-auto">
      <header className="mb-10 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <Link href="/" className="p-2 rounded-lg bg-white/5 text-slate-400 hover:text-white transition-smooth">
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <motion.h1 
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="text-3xl font-bold tracking-tight text-white"
            >
              Live & Recent Calls
            </motion.h1>
          </div>
          <motion.p 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.1 }}
            className="text-slate-400"
          >
            Monitor real-time support sessions and transcript logs
          </motion.p>
        </div>
      </header>

      {error && (
        <div className="mb-6 p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 text-sm">
          ⚠️ Running in offline demo mode: {error}. Make sure the backend is active at http://localhost:8000.
        </div>
      )}

      {/* Recent Calls Table */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.5 }}
        className="glass-panel rounded-2xl overflow-hidden"
      >
        <div className="p-6 border-b border-white/5">
          <h2 className="text-xl font-semibold text-white">Call Logs</h2>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-white/5 text-slate-400">
              <tr>
                <th className="px-6 py-4 font-medium">Call ID</th>
                <th className="px-6 py-4 font-medium">Intent</th>
                <th className="px-6 py-4 font-medium">Sentiment</th>
                <th className="px-6 py-4 font-medium">Status</th>
                <th className="px-6 py-4 font-medium">Started At</th>
                <th className="px-6 py-4 font-medium text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {loading && calls.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-slate-500">Loading calls...</td>
                </tr>
              ) : calls.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-slate-500">No calls active yet. Run voice_client.py to start a call.</td>
                </tr>
              ) : (
                calls.map((call) => (
                  <tr key={call.call_id} className="hover:bg-white/[0.02] transition-smooth group">
                    <td className="px-6 py-4 font-mono text-slate-300">
                      {call.call_id.length > 12 ? `${call.call_id.substring(0, 8)}...` : call.call_id}
                    </td>
                    <td className="px-6 py-4 text-slate-300 capitalize">
                      {call.intent?.replace("_", " ") || "Connecting..."}
                    </td>
                    <td className="px-6 py-4">
                      <span className={cn(
                        "px-2.5 py-1 rounded-full text-xs font-medium capitalize",
                        call.sentiment === "positive" ? "bg-emerald-500/10 text-emerald-400" :
                        call.sentiment === "angry" ? "bg-rose-500/10 text-rose-400" :
                        call.sentiment === "neutral" ? "bg-slate-500/10 text-slate-400" :
                        "bg-white/5 text-slate-500"
                      )}>
                        {call.sentiment || "Analyzing..."}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={cn(
                        "px-2.5 py-1 rounded-full text-xs font-medium capitalize",
                        call.status === "active" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" :
                        call.resolved ? "bg-blue-500/10 text-blue-400 border border-blue-500/20" : 
                        "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                      )}>
                        {call.status === "active" ? "Live" : call.resolved ? "Resolved" : "Escalated"}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-slate-400">
                      {call.started_at ? new Date(call.started_at).toLocaleTimeString() : "-"}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Link 
                        href={`/calls/${call.call_id}`}
                        className="px-3 py-1.5 rounded-lg bg-blue-500 text-white text-xs font-medium hover:bg-blue-600 transition-smooth"
                      >
                        {call.status === "active" ? "Join Call" : "View Logs"}
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
