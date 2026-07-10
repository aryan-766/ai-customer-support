"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Settings as SettingsIcon, Shield, Server, MessageSquare, Save, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("ai");
  const [saving, setSaving] = useState(false);

  const handleSave = () => {
    setSaving(true);
    setTimeout(() => setSaving(false), 800);
  };

  return (
    <div className="p-8 pb-20 max-w-5xl mx-auto">
      <header className="mb-10">
        <motion.h1 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="text-4xl font-bold tracking-tight text-white mb-2 flex items-center gap-3"
        >
          <SettingsIcon className="w-8 h-8 text-slate-400" />
          Settings
        </motion.h1>
        <motion.p 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="text-slate-400 text-lg ml-11"
        >
          Configure AI persona, API keys, and telephony webhooks
        </motion.p>
      </header>

      <div className="flex flex-col md:flex-row gap-8">
        {/* Sidebar Tabs */}
        <motion.aside 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
          className="w-full md:w-64 shrink-0 space-y-2"
        >
          <button 
            onClick={() => setActiveTab("ai")}
            className={cn(
              "w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-smooth",
              activeTab === "ai" ? "bg-white/10 text-white shadow-lg" : "text-slate-400 hover:text-white hover:bg-white/5"
            )}
          >
            <MessageSquare className="w-4 h-4" />
            AI Persona
          </button>
          <button 
            onClick={() => setActiveTab("integrations")}
            className={cn(
              "w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-smooth",
              activeTab === "integrations" ? "bg-white/10 text-white shadow-lg" : "text-slate-400 hover:text-white hover:bg-white/5"
            )}
          >
            <Shield className="w-4 h-4" />
            Integrations
          </button>
          <button 
            onClick={() => setActiveTab("telephony")}
            className={cn(
              "w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-smooth",
              activeTab === "telephony" ? "bg-white/10 text-white shadow-lg" : "text-slate-400 hover:text-white hover:bg-white/5"
            )}
          >
            <Server className="w-4 h-4" />
            Telephony & SIP
          </button>
        </motion.aside>

        {/* Content Area */}
        <motion.div 
          key={activeTab}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="flex-1 glass-panel rounded-2xl p-8 border border-white/5 relative"
        >
          {activeTab === "ai" && (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold text-white border-b border-white/5 pb-4 mb-6">AI Voice Persona</h2>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">TTS Voice Provider</label>
                  <select className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-slate-200 focus:outline-none focus:border-blue-500 transition-smooth">
                    <option value="elevenlabs">ElevenLabs (Premium)</option>
                    <option value="deepgram">Deepgram Aura</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Voice ID (ElevenLabs)</label>
                  <input type="text" defaultValue="21m00Tcm4TlvDq8ikWAM" className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-slate-200 focus:outline-none focus:border-blue-500 transition-smooth font-mono text-sm" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Base System Prompt</label>
                  <textarea rows={4} defaultValue="You are a polite, helpful customer support agent for Ambrane..." className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-slate-200 focus:outline-none focus:border-blue-500 transition-smooth resize-none"></textarea>
                </div>
              </div>
            </div>
          )}

          {activeTab === "integrations" && (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold text-white border-b border-white/5 pb-4 mb-6">CRM & Ticketing</h2>
              
              <div className="space-y-6">
                {/* Shopify */}
                <div className="p-5 rounded-xl border border-white/5 bg-white/[0.02]">
                  <h3 className="text-sm font-semibold text-emerald-400 mb-4 flex items-center gap-2">
                    <Zap className="w-4 h-4" /> Shopify CRM (Orders & Warranty)
                  </h3>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-xs text-slate-400 mb-1">Shop URL</label>
                      <input type="text" defaultValue="ambrane-store.myshopify.com" className="w-full bg-slate-900/50 border border-slate-800 rounded-lg px-3 py-2 text-slate-300 text-sm focus:outline-none focus:border-emerald-500 transition-smooth" />
                    </div>
                    <div>
                      <label className="block text-xs text-slate-400 mb-1">Admin API Access Token</label>
                      <input type="password" defaultValue="shpat_abcdef1234567890" className="w-full bg-slate-900/50 border border-slate-800 rounded-lg px-3 py-2 text-slate-300 text-sm focus:outline-none focus:border-emerald-500 transition-smooth font-mono" />
                    </div>
                  </div>
                </div>

                {/* Zoho Desk */}
                <div className="p-5 rounded-xl border border-white/5 bg-white/[0.02]">
                  <h3 className="text-sm font-semibold text-blue-400 mb-4 flex items-center gap-2">
                    <Shield className="w-4 h-4" /> Zoho Desk (Ticketing)
                  </h3>
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs text-slate-400 mb-1">Client ID</label>
                        <input type="password" defaultValue="1000.XXXXX" className="w-full bg-slate-900/50 border border-slate-800 rounded-lg px-3 py-2 text-slate-300 text-sm focus:outline-none focus:border-blue-500 transition-smooth" />
                      </div>
                      <div>
                        <label className="block text-xs text-slate-400 mb-1">Org ID</label>
                        <input type="text" defaultValue="654321098" className="w-full bg-slate-900/50 border border-slate-800 rounded-lg px-3 py-2 text-slate-300 text-sm focus:outline-none focus:border-blue-500 transition-smooth font-mono" />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "telephony" && (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold text-white border-b border-white/5 pb-4 mb-6">San Software SIP / Asterisk</h2>
              
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/20 mb-6">
                  <p className="text-sm text-blue-300 leading-relaxed">
                    Provide the webhook below to your Asterisk dialplan or San Software dashboard. This endpoint returns routing instructions to bridge the SIP audio to our AI WebSocket.
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">Incoming Call Webhook URL</label>
                  <div className="flex gap-2">
                    <input readOnly value="https://api.ambrane-ai.com/api/v1/sip/san-software/incoming" className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-slate-400 font-mono text-sm opacity-80" />
                    <button className="px-4 py-3 bg-white/10 hover:bg-white/20 text-white rounded-xl transition-smooth font-medium text-sm">Copy</button>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="mt-8 pt-6 border-t border-white/5 flex justify-end">
            <button 
              onClick={handleSave}
              disabled={saving}
              className="px-6 py-2.5 bg-white text-slate-950 font-semibold rounded-xl hover:bg-slate-200 transition-smooth flex items-center gap-2 disabled:opacity-70"
            >
              <Save className="w-4 h-4" />
              {saving ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
