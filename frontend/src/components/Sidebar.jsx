import React from 'react';
import { Sparkles, PieChart as PieIcon, TrendingUp, BarChart2, LogOut, BrainCircuit } from 'lucide-react'; 

export default function Sidebar({ activeTab, setActiveTab, logout }) {
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
          <button 
            onClick={() => setActiveTab('overview')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-medium whitespace-nowrap text-sm transition ${
              activeTab === 'overview' 
                ? 'bg-indigo-600/10 text-indigo-400 border border-indigo-500/20' 
                : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
            }`}
          >
            <PieIcon className="w-5 h-5 shrink-0" /> Analytics Overview
          </button>

          <button 
            onClick={() => setActiveTab('trends')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-medium whitespace-nowrap text-sm transition ${
              activeTab === 'trends' 
                ? 'bg-indigo-600/10 text-indigo-400 border border-indigo-500/20' 
                : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
            }`}
          >
            <BarChart2 className="w-5 h-5 shrink-0" /> Spending Trends
          </button>

          <button 
            onClick={() => setActiveTab('models')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-medium whitespace-nowrap text-sm transition ${
              activeTab === 'models' 
                ? 'bg-indigo-600/10 text-indigo-400 border border-indigo-500/20' 
                : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
            }`}
          >
            <BrainCircuit className="w-5 h-5 shrink-0" /> AI Data Models
          </button>
          
          <button 
            onClick={() => setActiveTab('history')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-medium whitespace-nowrap text-sm transition ${
              activeTab === 'history' 
                ? 'bg-indigo-600/10 text-indigo-400 border border-indigo-500/20' 
                : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
            }`}
          >
            <TrendingUp className="w-5 h-5 shrink-0" /> Budget History
          </button>
        </nav>
      </div>

      <div>
        <button 
          onClick={logout}
          className="w-full flex items-center gap-3 px-4 py-3 mb-4 rounded-xl text-rose-400 hover:bg-rose-500/10 hover:border-rose-500/20 border border-transparent transition whitespace-nowrap text-sm font-medium"
        >
          <LogOut className="w-5 h-5 shrink-0" /> Logout
        </button>

        <div className="p-4 bg-slate-800/40 border border-slate-800 rounded-2xl text-xs text-slate-400">
          <p className="font-semibold text-slate-300 mb-1">GHRCEM MCA Project</p>
          <p>Smart Expense Analyzer v1.0</p>
        </div>
      </div>
    </aside>
  );
}