import React from 'react';
import { Sparkles, PieChart as PieIcon, TrendingUp, ShieldAlert } from 'lucide-react';

export default function Sidebar() {
  return (
    <aside className="w-64 h-screen sticky top-0 border-r border-slate-800 bg-slate-900/50 p-6 flex flex-col justify-between hidden md:flex">
      <div>
        <div className="flex items-center gap-3 mb-10">
          <div className="p-2 bg-indigo-600 rounded-xl shadow-lg shadow-indigo-500/30">
            <Sparkles className="w-6 h-6 text-white" />
          </div>
          <span className="font-bold text-lg tracking-wide text-white">ExpenseAI</span>
        </div>

        <nav className="space-y-2">
          <button className="w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-indigo-600/10 text-indigo-400 font-medium border border-indigo-500/20 whitespace-nowrap text-sm">
            <PieIcon className="w-5 h-5 shrink-0" /> Analytics Overview
          </button>
          <button className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-slate-400 hover:bg-slate-800/50 hover:text-slate-200 transition whitespace-nowrap text-sm">
            <TrendingUp className="w-5 h-5 shrink-0" /> Spending Forecast
          </button>
          <button className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-slate-400 hover:bg-slate-800/50 hover:text-slate-200 transition whitespace-nowrap text-sm">
            <ShieldAlert className="w-5 h-5 shrink-0" /> Anomaly Detector
          </button>
        </nav>
      </div>

      <div className="p-4 bg-slate-800/40 border border-slate-800 rounded-2xl text-xs text-slate-400">
        <p className="font-semibold text-slate-300 mb-1">GHRCEM MCA Project</p>
        <p>Smart Expense Analyzer v1.0</p>
      </div>
    </aside>
  );
}