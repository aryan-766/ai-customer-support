"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Mic, SignalHigh, WifiOff, ListFilter } from "lucide-react";
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
  customer_phone?: string;
  duration?: string;
  caller_location?: string;
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
      } catch (err: unknown) {
        console.error("Error fetching calls:", err);
        setError(err instanceof Error ? err.message : "Failed to load calls");
        // Fallback rich mock data for presentation
        setCalls([
          { call_id: "c-live-9821", status: "active", intent: "order_status", sentiment: "neutral", priority: "high", resolved: false, started_at: new Date(Date.now() - 145000).toISOString(), customer_phone: "+91 98765 43210", duration: "02m 25s", caller_location: "Delhi, India" },
          { call_id: "c-live-9822", status: "active", intent: "warranty_check", sentiment: "angry", priority: "critical", resolved: false, started_at: new Date(Date.now() - 45000).toISOString(), customer_phone: "+91 87654 32109", duration: "00m 45s", caller_location: "Mumbai, India" },
          { call_id: "c-hist-1092", status: "completed", intent: "return_request", sentiment: "positive", priority: "medium", resolved: true, started_at: new Date(Date.now() - 3600000).toISOString(), customer_phone: "+91 76543 21098", duration: "04m 12s", caller_location: "Bangalore, India" },
          { call_id: "c-hist-1091", status: "escalated", intent: "technical_issue", sentiment: "negative", priority: "high", resolved: false, started_at: new Date(Date.now() - 7200000).toISOString(), customer_phone: "+91 65432 10987", duration: "11m 05s", caller_location: "Chennai, India" },
          { call_id: "c-hist-1090", status: "completed", intent: "general_inquiry", sentiment: "neutral", priority: "low", resolved: true, started_at: new Date(Date.now() - 14400000).toISOString(), customer_phone: "+91 54321 09876", duration: "01m 30s", caller_location: "Pune, India" },
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
    <div className="p-8 pb-20 max-w-[1600px] mx-auto">
      <header className="mb-10 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <Link href="/" className="p-2 rounded-lg bg-white/5 text-slate-400 hover:text-white hover:bg-white/10 transition-smooth">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <motion.h1 
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="text-4xl font-bold tracking-tight text-white bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent"
            >
              Call Monitoring
            </motion.h1>
          </div>
          <motion.p 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.1 }}
            className="text-slate-400 ml-12 text-lg"
          >
            Live agent supervision and session logs
          </motion.p>
        </div>
        
        <div className="flex items-center gap-4">
          <button className="glass-panel px-4 py-2.5 rounded-xl text-sm font-medium text-slate-300 hover:text-white flex items-center gap-2 border border-white/10 hover:border-white/20 transition-smooth">
            <ListFilter className="w-4 h-4" />
            Filter
          </button>
        </div>
      </header>

      {error && (
        <motion.div 
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8 p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-start gap-3"
        >
          <WifiOff className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <h4 className="text-sm font-semibold text-amber-400 mb-1">Running in Offline Demo Mode</h4>
            <p className="text-sm text-amber-400/80 leading-relaxed">
              {error}. Displaying mock data for presentation purposes. Make sure the backend is active at <code className="bg-black/20 px-1.5 py-0.5 rounded">http://localhost:8000</code>.
            </p>
          </div>
        </motion.div>
      )}

      {/* Main Grid Layout for Live vs Historical */}
      <div className="grid grid-cols-1 gap-8">
        {/* Live Active Calls Section */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.5 }}
        >
          <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
            </span>
            Active Sessions ({calls.filter(c => c.status === 'active').length})
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {calls.filter(c => c.status === 'active').map((call) => (
              <div key={call.call_id} className="glass-panel rounded-2xl p-6 border border-emerald-500/20 relative overflow-hidden group">
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-emerald-500 to-blue-500" />
                
                <div className="flex justify-between items-start mb-6">
                  <div>
                    <h3 className="text-lg font-bold text-white mb-1">{call.customer_phone || "Unknown Caller"}</h3>
                    <p className="text-xs text-slate-400 flex items-center gap-1.5">
                      <SignalHigh className="w-3 h-3 text-emerald-400" />
                      {call.caller_location || "Connecting..."}
                    </p>
                  </div>
                  <div className="px-3 py-1 bg-emerald-500/10 text-emerald-400 rounded-full text-xs font-semibold flex items-center gap-1.5 border border-emerald-500/20 shadow-[0_0_15px_rgba(16,185,129,0.15)]">
                    <Mic className="w-3 h-3 animate-pulse" />
                    LIVE
                  </div>
                </div>

                <div className="space-y-4 mb-6">
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-slate-400">Intent Analysis</span>
                    <span className="text-white capitalize font-medium">{call.intent?.replace("_", " ") || "Detecting..."}</span>
                  </div>
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-slate-400">Customer Mood</span>
                    <span className={cn(
                      "font-medium flex items-center gap-1.5",
                      call.sentiment === "angry" ? "text-rose-400" :
                      call.sentiment === "positive" ? "text-emerald-400" :
                      "text-slate-300"
                    )}>
                      {call.sentiment === "angry" && "⚠️ "}
                      <span className="capitalize">{call.sentiment || "Neutral"}</span>
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-slate-400">Duration</span>
                    <span className="text-slate-300 font-mono">{call.duration || "00m 00s"}</span>
                  </div>
                </div>

                <Link 
                  href={`/calls/${call.call_id}`}
                  className="w-full block text-center bg-blue-600 hover:bg-blue-500 text-white font-medium py-2.5 rounded-xl transition-all shadow-[0_0_20px_rgba(37,99,235,0.2)] hover:shadow-[0_0_25px_rgba(37,99,235,0.4)]"
                >
                  Join Transcription Stream
                </Link>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Historical Calls Table */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.5 }}
          className="mt-4"
        >
          <h2 className="text-xl font-semibold text-white mb-4">Historical Logs</h2>
          <div className="glass-panel rounded-2xl overflow-hidden border border-white/5">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm whitespace-nowrap">
                <thead className="bg-slate-900/50 text-slate-400 border-b border-white/5">
                  <tr>
                    <th className="px-6 py-4 font-medium">Session ID</th>
                    <th className="px-6 py-4 font-medium">Customer</th>
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
                      <td colSpan={7} className="px-6 py-12 text-center text-slate-500">Loading calls...</td>
                    </tr>
                  ) : calls.filter(c => c.status !== 'active').length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-6 py-12 text-center text-slate-500">No historical calls found.</td>
                    </tr>
                  ) : (
                    calls.filter(c => c.status !== 'active').map((call) => (
                      <tr key={call.call_id} className="hover:bg-white/[0.03] transition-smooth group relative">
                        <td className="px-6 py-4 font-mono text-slate-400">
                          {call.call_id}
                        </td>
                        <td className="px-6 py-4 font-medium text-slate-300">
                          {call.customer_phone || "Unknown"}
                        </td>
                        <td className="px-6 py-4 text-slate-400 capitalize">
                          {call.intent?.replace("_", " ") || "Unknown"}
                        </td>
                        <td className="px-6 py-4">
                          <span className={cn(
                            "px-2.5 py-1 rounded-full text-xs font-medium capitalize inline-flex items-center gap-1.5",
                            call.sentiment === "positive" ? "bg-emerald-500/10 text-emerald-400" :
                            call.sentiment === "angry" ? "bg-rose-500/10 text-rose-400" :
                            call.sentiment === "negative" ? "bg-rose-500/10 text-rose-400" :
                            "bg-slate-500/10 text-slate-400"
                          )}>
                            {call.sentiment || "Neutral"}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <span className={cn(
                            "px-2.5 py-1 rounded-full text-xs font-medium capitalize",
                            call.resolved ? "bg-blue-500/10 text-blue-400 border border-blue-500/20" : 
                            "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                          )}>
                            {call.resolved ? "Resolved" : "Escalated"}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-slate-500">
                          {new Date(call.started_at).toLocaleString()}
                        </td>
                        <td className="px-6 py-4 text-right">
                          <Link 
                            href={`/calls/${call.call_id}`}
                            className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white text-xs font-medium transition-smooth"
                          >
                            View Summary
                          </Link>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
