import React, { useState } from 'react';
import { Sparkles, CheckCircle2, Loader2 } from 'lucide-react';

export default function BudgetOptimizer({ recommendations = [], activeBudgets = {} }) {
  const [selectedIds, setSelectedIds] = useState(recommendations.map(r => r.id));
  const [isProcessing, setIsProcessing] = useState(false);
  const [optimizationResult, setOptimizationResult] = useState(null);

  const toggleSelection = (id) => {
    setOptimizationResult(null);
    setSelectedIds(prev => 
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const handleApplyAI = async () => {
    if (selectedIds.length === 0) return;
    setIsProcessing(true);

    const activeRecs = recommendations.filter(r => selectedIds.includes(r.id));
    const categoriesToOptimize = activeRecs.map(r => r.title.replace(/^(Optimize|Cap)\s+|\s+(Spend|Budget)$/g, '').trim());

    try {
      const res = await fetch('http://127.0.0.1:8000/api/optimize/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          categories: categoriesToOptimize,
          target_month: '2026-09' // You can make this dynamic if needed
        })
      });
      const data = await res.json();
      setOptimizationResult(data);
    } catch (err) {
      console.error("AI Optimization error:", err);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="lg:col-span-5 p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl backdrop-blur-sm flex flex-col justify-between">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <Sparkles className="w-5 h-5 text-indigo-400" />
          <h3 className="text-lg font-bold text-white">AI Budget Optimization</h3>
        </div>
        <p className="text-xs text-slate-400">
          Apriori association rule mining + Linear Programming recommendations
        </p>
      </div>

      <div className="space-y-3 my-4">
        {recommendations.length > 0 ? (
          recommendations.map((rec) => {
            const isSelected = selectedIds.includes(rec.id);
            return (
              <div
                key={rec.id}
                onClick={() => toggleSelection(rec.id)}
                className={`p-4 rounded-xl border transition-all cursor-pointer flex items-start justify-between gap-3 ${
                  isSelected 
                    ? 'bg-slate-800/60 border-indigo-500/50 shadow-lg shadow-indigo-500/5' 
                    : 'bg-slate-800/20 border-slate-800 opacity-60 hover:opacity-100'
                }`}
              >
                <div>
                  <h4 className={`text-sm font-semibold mb-1 ${isSelected ? 'text-indigo-300' : 'text-slate-400'}`}>
                    {rec.title}
                  </h4>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    {rec.description}
                  </p>
                </div>
                <div className="mt-0.5">
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => {}} 
                    className="w-4 h-4 rounded border-slate-700 bg-slate-900 text-indigo-600 focus:ring-indigo-500 cursor-pointer"
                  />
                </div>
              </div>
            );
          })
        ) : (
          <div className="p-8 text-center text-xs text-slate-500">
            No optimization strategies available yet. Upload a transaction statement to begin.
          </div>
        )}
      </div>

      {/* Show currently active saved budget limits if any exist */}
      {Object.keys(activeBudgets).length > 0 && (
        <div className="mb-4 p-3 bg-slate-800/40 border border-slate-700/60 rounded-xl">
          <p className="text-xs font-semibold text-slate-300 mb-2">Active Committed Budget Caps:</p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(activeBudgets).map(([cat, cap]) => (
              <span key={cat} className="px-2.5 py-1 bg-indigo-950/60 border border-indigo-500/30 text-indigo-300 rounded-lg text-[11px]">
                {cat}: <strong>₹{cap}</strong>
              </span>
            ))}
          </div>
        </div>
      )}

      <div>
        <button
          onClick={handleApplyAI}
          disabled={selectedIds.length === 0 || isProcessing}
          className={`w-full py-3 px-4 rounded-xl font-medium text-xs transition duration-200 shadow-lg flex items-center justify-center gap-2 ${
            selectedIds.length > 0 && !isProcessing
              ? 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-600/20 cursor-pointer'
              : 'bg-slate-800 text-slate-500 cursor-not-allowed'
          }`}
        >
          {isProcessing ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Running Linear Programming Solver...</span>
            </>
          ) : (
            'Apply Optimization Strategy'
          )}
        </button>

        {optimizationResult && (
          <div className="mt-3 p-3 bg-indigo-950/40 border border-indigo-500/30 rounded-xl space-y-1 text-indigo-300 text-xs animate-fade-in">
            <div className="flex items-center gap-2 font-semibold">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>Linear Programming Constraints Saved!</span>
            </div>
            <p className="text-slate-400">
              Committed monthly caps permanently stored. Total optimized target savings: <strong className="text-white">₹{optimizationResult.total_optimized_savings}</strong>
            </p>
          </div>
        )}
      </div>
    </div>
  );
}