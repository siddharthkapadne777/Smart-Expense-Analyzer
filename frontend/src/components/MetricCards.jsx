import React from 'react';
import { DollarSign, ArrowUpRight, TrendingUp, AlertTriangle, CheckCircle2 } from 'lucide-react';

export default function MetricCards({ metrics, totalForecastSpend }) {
  return (
    <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
      <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl relative overflow-hidden backdrop-blur-sm">
        <div className="flex justify-between items-start">
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Analyzed Spend</p>
            <h3 className="text-2xl font-bold text-white mt-2">
              ₹{metrics.total_spend ? metrics.total_spend.toLocaleString() : '0.00'}
            </h3>
          </div>
          <div className="p-2.5 bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 rounded-xl">
            <DollarSign className="w-5 h-5" />
          </div>
        </div>
        <div className="mt-4 flex items-center text-xs text-emerald-400 font-medium gap-1">
          <ArrowUpRight className="w-4 h-4" /> {metrics.total_transactions} Transactions processed
        </div>
      </div>

      <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl relative overflow-hidden backdrop-blur-sm">
        <div className="flex justify-between items-start">
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">7-Day Forecasted Spend</p>
            <h3 className="text-2xl font-bold text-white mt-2">
              ₹{totalForecastSpend.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </h3>
          </div>
          <div className="p-2.5 bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-xl">
            <TrendingUp className="w-5 h-5" />
          </div>
        </div>
        <p className="mt-4 text-xs text-slate-400">Based on Linear Regression models</p>
      </div>

      <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl relative overflow-hidden backdrop-blur-sm">
        <div className="flex justify-between items-start">
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Flagged Outliers</p>
            <h3 className="text-2xl font-bold text-rose-400 mt-2">{metrics.anomalies ? metrics.anomalies.length : 0} Suspicious Items</h3>
          </div>
          <div className="p-2.5 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-xl">
            <AlertTriangle className="w-5 h-5" />
          </div>
        </div>
        <p className="mt-4 text-xs text-slate-400">Detected via Isolation Forest</p>
      </div>

      <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl relative overflow-hidden backdrop-blur-sm">
        <div className="flex justify-between items-start">
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Recommended Savings</p>
            <h3 className="text-2xl font-bold text-emerald-400 mt-2">
              ₹{metrics.recommended_savings ? metrics.recommended_savings.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '0.00'} / mo
            </h3>
          </div>
          <div className="p-2.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-xl">
            <CheckCircle2 className="w-5 h-5" />
          </div>
        </div>
        <p className="mt-4 text-xs text-slate-400">Optimized via SciPy Linear Programming</p>
      </div>
    </section>
  );
}