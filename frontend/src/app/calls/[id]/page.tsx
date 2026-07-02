"use client";

import { useEffect, useState, useRef } from "react";
import { use } from "react";
import { motion } from "framer-motion";
import { Mic, User, Bot, AlertCircle, FileText } from "lucide-react";
import { cn } from "@/lib/utils";

interface Message {
  id: string;
  speaker: "customer" | "ai" | "system";
  text: string;
  timestamp: string;
}

interface Suggestion {
  suggestion: string;
  kb_reference: string | null;
  compliance_alert: string | null;
}

export default function LiveCallView({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const callId = resolvedParams.id;
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [status, setStatus] = useState<"connecting" | "live" | "ended" | "error">("connecting");
  const wsRef = useRef<WebSocket | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    // 1. Fetch transcript history to display the greeting and previous conversation immediately
    async function fetchHistory() {
      try {
        const res = await fetch(`http://localhost:8000/api/v1/calls/${callId}/transcript`);
        if (res.ok) {
          const data = await res.json();
          if (data.transcript) {
            setMessages(data.transcript.map((t: any) => ({
              id: Math.random().toString(),
              speaker: t.speaker === "receptionist" ? "ai" : t.speaker === "ai" ? "ai" : "customer",
              text: t.text,
              timestamp: new Date(t.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            })));
          }
        }
      } catch (err) {
        console.error("Failed to fetch transcript history:", err);
      }
    }

    fetchHistory();

    // 2. Connect to the human agent WebSocket for this specific call/agent
    // In a real app, agent_id would come from auth context. Using callId as mock agent_id for demo.
    const ws = new WebSocket(`ws://localhost:8000/ws/agent/${callId}`);
    wsRef.current = ws;

    ws.onopen = () => setStatus("live");
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === "transcript_chunk") {
          setMessages(prev => [...prev, {
            id: Date.now().toString() + Math.random(),
            speaker: data.speaker === "receptionist" ? "ai" : data.speaker === "ai" ? "ai" : "customer",
            text: data.text,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          }]);
        } 
        else if (data.type === "assist_suggestion") {
          setSuggestions(data.data);
        }
        else if (data.type === "call_ended") {
          setStatus("ended");
        }
      } catch (e) {
        console.error("Failed to parse WS message", e);
      }
    };

    ws.onerror = () => setStatus("error");
    ws.onclose = () => setStatus("ended");

    return () => {
      ws.close();
    };
  }, [callId]);

  return (
    <div className="flex h-screen p-6 gap-6">
      
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col glass-panel rounded-2xl overflow-hidden">
        {/* Header */}
        <div className="h-20 border-b border-white/5 flex items-center justify-between px-8 bg-white/[0.02]">
          <div>
            <h1 className="text-xl font-bold text-white flex items-center gap-3">
              Live Call <span className="text-slate-500 font-mono text-sm">#{callId.substring(0,8)}</span>
            </h1>
            <div className="flex items-center gap-2 mt-1">
              <span className="relative flex h-2.5 w-2.5">
                {status === "live" && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>}
                <span className={cn(
                  "relative inline-flex rounded-full h-2.5 w-2.5",
                  status === "live" ? "bg-emerald-500" : status === "connecting" ? "bg-amber-500" : "bg-slate-500"
                )}></span>
              </span>
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                {status}
              </span>
            </div>
          </div>
          
          <div className="flex gap-3">
            <button className="px-4 py-2 rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20 hover:bg-rose-500/20 transition-smooth text-sm font-medium">
              End Call
            </button>
            <button className="px-4 py-2 rounded-lg bg-blue-500 text-white shadow-lg shadow-blue-500/25 hover:bg-blue-600 transition-smooth text-sm font-medium">
              Takeover
            </button>
          </div>
        </div>

        {/* Transcript */}
        <div 
          ref={scrollRef}
          className="flex-1 overflow-y-auto p-8 space-y-6 scroll-smooth"
        >
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-slate-500 space-y-4">
              <Mic className="w-12 h-12 opacity-20" />
              <p>Waiting for audio stream...</p>
            </div>
          ) : (
            messages.map((msg, i) => (
              <motion.div 
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                key={msg.id} 
                className={cn(
                  "flex gap-4 max-w-[80%]",
                  msg.speaker === "customer" ? "mr-auto" : "ml-auto flex-row-reverse"
                )}
              >
                <div className={cn(
                  "w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 shadow-lg",
                  msg.speaker === "customer" 
                    ? "bg-slate-800 border border-white/10 text-slate-300"
                    : "bg-gradient-to-tr from-blue-600 to-purple-600 text-white"
                )}>
                  {msg.speaker === "customer" ? <User size={18} /> : <Bot size={18} />}
                </div>
                
                <div className={cn(
                  "p-4 rounded-2xl relative group",
                  msg.speaker === "customer" 
                    ? "bg-white/5 border border-white/10 rounded-tl-sm text-slate-200"
                    : "bg-blue-500/10 border border-blue-500/20 rounded-tr-sm text-blue-50"
                )}>
                  <p className="leading-relaxed">{msg.text}</p>
                  <span className="text-[10px] text-slate-500 absolute -bottom-5 right-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    {msg.timestamp}
                  </span>
                </div>
              </motion.div>
            ))
          )}
        </div>
      </div>

      {/* Right Sidebar: Agent Assist */}
      <div className="w-96 flex flex-col gap-6">
        
        {/* Real-time AI Suggestions */}
        <div className="flex-1 glass-panel rounded-2xl overflow-hidden flex flex-col">
          <div className="p-5 border-b border-white/5 bg-gradient-to-r from-blue-500/10 to-transparent">
            <h2 className="font-semibold text-white flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-blue-400" />
              Agent Assist
            </h2>
            <p className="text-xs text-slate-400 mt-1">Live AI suggestions & policies</p>
          </div>
          
          <div className="p-5 flex-1 overflow-y-auto space-y-4">
            {suggestions.length === 0 ? (
              <p className="text-sm text-slate-500 italic text-center mt-10">
                Listening for context...
              </p>
            ) : (
              suggestions.map((sug, i) => (
                <motion.div 
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  key={i} 
                  className="p-4 rounded-xl bg-white/5 border border-white/10 hover:border-blue-500/30 transition-smooth"
                >
                  <p className="text-sm text-slate-200 leading-relaxed font-medium">
                    "{sug.suggestion}"
                  </p>
                  
                  {sug.kb_reference && (
                    <div className="mt-3 pt-3 border-t border-white/5 flex items-start gap-2 text-xs text-slate-400">
                      <FileText className="w-3.5 h-3.5 mt-0.5 text-blue-400" />
                      <span>Ref: <span className="text-blue-300">{sug.kb_reference}</span></span>
                    </div>
                  )}
                  
                  {sug.compliance_alert && (
                    <div className="mt-2 flex items-start gap-2 text-xs text-amber-400 bg-amber-400/10 p-2 rounded-lg border border-amber-400/20">
                      <AlertCircle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                      <span>{sug.compliance_alert}</span>
                    </div>
                  )}
                </motion.div>
              ))
            )}
          </div>
        </div>
        
        {/* Quick Actions */}
        <div className="h-64 glass-panel rounded-2xl p-5">
          <h2 className="font-semibold text-white mb-4">Quick Actions</h2>
          <div className="space-y-2">
            {["Verify Warranty", "Send Payment Link", "Schedule Callback", "Create Zoho Ticket"].map(action => (
              <button key={action} className="w-full text-left px-4 py-3 rounded-xl bg-white/5 hover:bg-white/10 text-sm font-medium text-slate-300 transition-smooth border border-transparent hover:border-white/10">
                {action}
              </button>
            ))}
          </div>
        </div>
        
      </div>
      
    </div>
  );
}
