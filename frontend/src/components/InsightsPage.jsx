import React, { useState, useEffect } from 'react';
import { Loader2, Lightbulb, TrendingUp } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export default function InsightsPage() {
    const { token } = useAuth();
    const [insights, setInsights] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch(`${API_BASE}/api/insights/`, {
            headers: { 'Authorization': `Token ${token}` }
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') setInsights(data.insights);
            setLoading(false);
        })
        .catch(err => {
            console.error(err);
            setLoading(false);
        });
    }, [token]);

    return (
        <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl backdrop-blur-sm min-h-[500px]">
            <div className="mb-8">
                <h3 className="text-xl font-bold text-white flex items-center gap-2">
                    <Lightbulb className="w-6 h-6 text-amber-400" />
                    Smart Spending Insights
                </h3>
                <p className="text-xs text-slate-400 mt-1">
                    Powered by Apriori Association Rule Mining (Data Mining)
                </p>
            </div>

            {loading ? (
                <div className="h-[300px] flex items-center justify-center">
                    <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
                </div>
            ) : insights.length === 0 ? (
                <div className="text-center py-20 text-slate-500">
                    <Lightbulb className="w-12 h-12 mx-auto mb-3 opacity-20" />
                    <p>Not enough data to find patterns yet.</p>
                    <p className="text-xs mt-1">Upload more transactions to unlock insights.</p>
                </div>
            ) : (
                <div className="grid gap-4 md:grid-cols-2">
                    {insights.map((insight, idx) => (
                        <div key={idx} className="p-5 bg-slate-800/40 border border-slate-700/60 rounded-xl hover:border-amber-500/30 transition">
                            <div className="flex items-start gap-3">
                                <div className="p-2 bg-amber-500/10 rounded-lg shrink-0">
                                    <TrendingUp className="w-5 h-5 text-amber-400" />
                                </div>
                                <div>
                                    <h4 className="text-sm font-semibold text-white mb-1">
                                        {insight.rule}
                                    </h4>
                                    <p className="text-xs text-slate-300">
                                        {insight.result}
                                    </p>
                                    <div className="mt-3 inline-block px-2 py-1 bg-amber-500/10 border border-amber-500/20 text-amber-300 text-[10px] rounded-md font-mono">
                                        {insight.confidence}% Confidence
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}