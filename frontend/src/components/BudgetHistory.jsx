import React, { useEffect, useState } from 'react';
import { CheckCircle2, XCircle, Clock, Loader2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export default function BudgetHistory() {
  const { token } = useAuth();
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/api/budget-history/`, {
      headers: { 'Authorization': `Token ${token}` }
    })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') setHistory(data.history);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, [token]);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-[300px]">
        <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
      </div>
    );
  }

  if (history.length === 0) {
    return (
      <div className="p-10 bg-slate-900/60 border border-slate-800/80 rounded-2xl text-center">
        <Clock className="w-10 h-10 text-slate-500 mx-auto mb-3" />
        <h3 className="text-white font-bold text-lg">No Budget History Yet</h3>
        <p className="text-slate-400 text-sm mt-1">Apply a budget optimization strategy to start tracking your success.</p>
      </div>
    );
  }

  return (
    <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl backdrop-blur-sm">
      <h3 className="text-lg font-bold text-white mb-1">Budget Performance History</h3>
      <p className="text-xs text-slate-400 mb-6">Track how well you stick to your committed monthly caps.</p>

      <div className="space-y-3">
        {history.map((item) => {
          const isSuccess = item.status === 'success';
          const isFailed = item.status === 'failed';
          const isTracking = item.status === 'in_progress';

          // Dynamic UI based on status
          let cardClass = 'bg-slate-800/40 border-slate-700/60';
          let icon = <Clock className="w-8 h-8 text-indigo-400 shrink-0" />;
          let textClass = 'text-indigo-400';
          let title = 'Tracking:';

          if (isSuccess) {
            cardClass = 'bg-emerald-950/20 border-emerald-500/30';
            icon = <CheckCircle2 className="w-8 h-8 text-emerald-400 shrink-0" />;
            textClass = 'text-emerald-400';
            title = 'Success:';
          } else if (isFailed) {
            cardClass = 'bg-rose-950/20 border-rose-500/30';
            icon = <XCircle className="w-8 h-8 text-rose-400 shrink-0" />;
            textClass = 'text-rose-400';
            title = 'Failed:';
          }

          return (
            <div 
              key={item.id} 
              className={`p-4 rounded-xl border flex items-center justify-between gap-4 ${cardClass}`}
            >
              <div className="flex items-center gap-4">
                {icon}
                <div>
                  <h4 className="text-white font-semibold text-sm">
                    {item.category} <span className="text-slate-500 text-xs font-normal ml-1">({item.month})</span>
                  </h4>
                  <p className={`text-xs mt-0.5 ${textClass}`}>
                    <span className="font-semibold">{title}</span> 
                    {isTracking 
                      ? ` ₹${(item.cap - item.actual_spend).toLocaleString()} remaining for this month.` 
                      : ` ${item.message} by ₹${item.difference.toLocaleString()}`}
                  </p>
                </div>
              </div>

              <div className="text-right shrink-0">
                <p className="text-xs text-slate-400">Spend / Cap</p>
                <p className="text-sm font-bold text-white mt-0.5">
                  ₹{item.actual_spend.toLocaleString()} / <span className="text-slate-500">₹{item.cap.toLocaleString()}</span>
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}