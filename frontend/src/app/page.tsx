"use client";

import { useEffect, useState } from "react";
import { KpiCard } from "@/components/KpiCard";
import { PhoneCall, CheckCircle, Clock, AlertTriangle, TrendingUp, BarChart3, Users } from "lucide-react";
import Link from "next/link";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';

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
  customer_phone?: string;
}

const chartData = [
  { time: '09:00', calls: 120, resolved: 90 },
  { time: '10:00', calls: 180, resolved: 140 },
  { time: '11:00', calls: 250, resolved: 200 },
  { time: '12:00', calls: 300, resolved: 220 },
  { time: '13:00', calls: 280, resolved: 210 },
  { time: '14:00', calls: 340, resolved: 270 },
  { time: '15:00', calls: 390, resolved: 310 },
  { time: '16:00', calls: 420, resolved: 350 },
  { time: '17:00', calls: 280, resolved: 240 },
];

const intentData = [
  { name: 'Order Status', value: 45 },
  { name: 'Warranty', value: 25 },
  { name: 'Return', value: 15 },
  { name: 'Technical', value: 10 },
  { name: 'Other', value: 5 },
];

export default function Dashboard() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [calls, setCalls] = useState<CallRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentTime, setCurrentTime] = useState(Date.now());

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    // In a real app, you'd fetch from http://localhost:8000/analytics/kpis
    setTimeout(() => {
      setData({
        total_calls: 3248,
        ai_resolution_rate: 0.84,
        human_transfer_rate: 0.16,
        avg_handle_time_sec: 112.5,
      });
      setCalls([
        { call_id: "c-live-9821", status: "active", intent: "order_status", sentiment: "neutral", priority: "high", resolved: false, started_at: new Date(Date.now() - 45000).toISOString(), customer_phone: "+91 98765 43210" },
        { call_id: "c-live-9822", status: "active", intent: "warranty_check", sentiment: "angry", priority: "critical", resolved: false, started_at: new Date(Date.now() - 120000).toISOString(), customer_phone: "+91 87654 32109" },
        { call_id: "c-hist-1092", status: "completed", intent: "return_request", sentiment: "positive", priority: "medium", resolved: true, started_at: new Date(Date.now() - 3600000).toISOString(), customer_phone: "+91 76543 21098" },
        { call_id: "c-hist-1091", status: "escalated", intent: "technical_issue", sentiment: "negative", priority: "high", resolved: false, started_at: new Date(Date.now() - 7200000).toISOString(), customer_phone: "+91 65432 10987" },
      ]);
      setLoading(false);
    }, 800);
  }, []);

  return (
    <div className="p-8 pb-20 max-w-[1600px] mx-auto">
      <header className="mb-10 flex justify-between items-end">
        <div>
          <motion.h1 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="text-4xl font-bold tracking-tight text-white mb-2 bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent"
          >
            Command Center
          </motion.h1>
          <motion.p 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.1 }}
            className="text-slate-400 text-lg"
          >
            Real-time AI voice operations and telephony metrics
          </motion.p>
        </div>
        <motion.div 
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
          className="flex gap-3"
        >
          <div className="glass-panel px-4 py-2 rounded-xl flex items-center gap-2 border border-emerald-500/20">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
            </span>
            <span className="text-sm font-medium text-emerald-400">System Healthy</span>
          </div>
        </motion.div>
      </header>

      {/* KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 mb-8">
        <KpiCard 
          title="Total Calls (Today)" 
          value={loading ? "-" : (data?.total_calls || 0).toLocaleString()} 
          icon={PhoneCall} 
          trend="18% vs yesterday"
          trendUp={true}
          delay={0.1}
        />
        <KpiCard 
          title="AI Resolution Rate" 
          value={loading ? "-" : `${((data?.ai_resolution_rate || 0) * 100).toFixed(1)}%`} 
          icon={CheckCircle} 
          trend="2.4% vs yesterday"
          trendUp={true}
          delay={0.2}
        />
        <KpiCard 
          title="Avg Handle Time" 
          value={loading ? "-" : `${Math.round((data?.avg_handle_time_sec || 0) / 60)}m ${Math.round((data?.avg_handle_time_sec || 0) % 60)}s`} 
          icon={Clock} 
          trend="12s faster"
          trendUp={true}
          delay={0.3}
        />
        <KpiCard 
          title="Escalation Rate" 
          value={loading ? "-" : `${((data?.human_transfer_rate || 0) * 100).toFixed(1)}%`} 
          icon={AlertTriangle} 
          trend="0.8% vs yesterday"
          trendUp={false}
          delay={0.4}
        />
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="lg:col-span-2 glass-panel rounded-2xl p-6 border border-white/5"
        >
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-blue-400" />
              Call Volume & Resolution Trend
            </h3>
          </div>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorCalls" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorResolved" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" vertical={false} />
                <XAxis dataKey="time" stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px' }}
                  itemStyle={{ color: '#f8fafc' }}
                />
                <Area type="monotone" dataKey="calls" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#colorCalls)" name="Total Calls" />
                <Area type="monotone" dataKey="resolved" stroke="#10b981" strokeWidth={2} fillOpacity={1} fill="url(#colorResolved)" name="AI Resolved" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="glass-panel rounded-2xl p-6 border border-white/5"
        >
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-indigo-400" />
              Top Intents
            </h3>
          </div>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={intentData} layout="vertical" margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" horizontal={false} />
                <XAxis type="number" stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} hide />
                <YAxis dataKey="name" type="category" stroke="#cbd5e1" fontSize={13} tickLine={false} axisLine={false} width={100} />
                <Tooltip 
                  cursor={{fill: '#ffffff05'}}
                  contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px' }}
                />
                <Bar dataKey="value" fill="#6366f1" radius={[0, 4, 4, 0]} barSize={24} name="% of Calls" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>
      </div>

      {/* Recent Calls Table */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.7 }}
        className="glass-panel rounded-2xl overflow-hidden border border-white/5"
      >
        <div className="p-6 border-b border-white/5 flex justify-between items-center bg-white/[0.02]">
          <h2 className="text-xl font-semibold text-white flex items-center gap-2">
            <Users className="w-5 h-5 text-slate-400" />
            Live & Recent Sessions
          </h2>
          <Link href="/calls" className="text-sm font-medium text-blue-400 hover:text-blue-300 transition-smooth px-4 py-2 rounded-lg hover:bg-blue-500/10">
            View all →
          </Link>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-slate-900/50 text-slate-400">
              <tr>
                <th className="px-6 py-4 font-medium">Session ID</th>
                <th className="px-6 py-4 font-medium">Customer</th>
                <th className="px-6 py-4 font-medium">Intent</th>
                <th className="px-6 py-4 font-medium">Sentiment</th>
                <th className="px-6 py-4 font-medium">Status</th>
                <th className="px-6 py-4 font-medium">Duration</th>
                <th className="px-6 py-4 font-medium text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center text-slate-500">Loading sessions...</td>
                </tr>
              ) : (
                calls.map((call) => {
                  const isLive = call.status === 'active';
                  const durationStr = isLive 
                    ? `${Math.floor((currentTime - new Date(call.started_at).getTime()) / 1000)}s`
                    : "04m 12s";

                  return (
                    <tr key={call.call_id} className="hover:bg-white/[0.03] transition-smooth group relative">
                      {isLive && (
                        <td className="absolute left-0 top-0 bottom-0 w-1 bg-emerald-500" />
                      )}
                      <td className="px-6 py-4 font-mono text-slate-300">
                        {call.call_id}
                      </td>
                      <td className="px-6 py-4 font-medium text-slate-200">
                        {call.customer_phone}
                      </td>
                      <td className="px-6 py-4 text-slate-300 capitalize">
                        {call.intent?.replace("_", " ") || "Unknown"}
                      </td>
                      <td className="px-6 py-4">
                        <span className={cn(
                          "px-2.5 py-1 rounded-full text-xs font-medium capitalize inline-flex items-center gap-1.5",
                          call.sentiment === "positive" ? "bg-emerald-500/10 text-emerald-400" :
                          call.sentiment === "angry" ? "bg-rose-500/10 text-rose-400" :
                          "bg-slate-500/10 text-slate-400"
                        )}>
                          {call.sentiment === "positive" && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />}
                          {call.sentiment === "angry" && <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />}
                          {call.sentiment === "negative" && <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />}
                          {call.sentiment === "neutral" && <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />}
                          {call.sentiment || "Neutral"}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className={cn(
                          "px-2.5 py-1 rounded-full text-xs font-medium capitalize",
                          isLive ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-[0_0_10px_rgba(16,185,129,0.2)]" :
                          call.resolved ? "bg-blue-500/10 text-blue-400 border border-blue-500/20" : 
                          "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                        )}>
                          {isLive ? (
                            <span className="flex items-center gap-1.5">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                              Live Call
                            </span>
                          ) : call.resolved ? "Resolved" : "Escalated"}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-slate-400 font-mono text-xs">
                        {durationStr}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <Link 
                          href={`/calls/${call.call_id}`}
                          className={cn(
                            "px-3 py-1.5 rounded-lg text-xs font-medium transition-smooth inline-block",
                            isLive 
                              ? "bg-emerald-500 text-white hover:bg-emerald-600 shadow-[0_0_15px_rgba(16,185,129,0.3)]" 
                              : "bg-white/10 text-white hover:bg-white/20 opacity-0 group-hover:opacity-100"
                          )}
                        >
                          {isLive ? "Monitor" : "View Details"}
                        </Link>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </motion.div>
    </div>
  );
}
