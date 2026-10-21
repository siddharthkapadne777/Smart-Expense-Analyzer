import React, { useState, useEffect } from 'react';
import { Scatter } from 'react-chartjs-2';
import { Chart as ChartJS, LinearScale, PointElement, Tooltip, Legend } from 'chart.js';
import { Loader2, BrainCircuit, Lightbulb } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

ChartJS.register(LinearScale, PointElement, Tooltip, Legend);
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export default function DataMiningPage() {
    const { token } = useAuth();
    const [data, setData] = useState({ scatter_data: [], apriori_insights: [] });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch(`${API_BASE}/api/data-mining/`, {
            headers: { 'Authorization': `Token ${token}` }
        })
        .then(res => res.json())
        .then(resData => {
            if (resData.status === 'success') {
                setData({
                    scatter_data: resData.scatter_data || [],
                    apriori_insights: resData.apriori_insights || []
                });
            }
            setLoading(false);
        })
        .catch(err => {
            console.error(err);
            setLoading(false);
        });
    }, [token]);

    // Prepare data for Chart.js Scatter Plot
    const clusterColors = ['#6366f1', '#ec4899', '#10b981', '#f59e0b', '#8b5cf6'];
    const clusters = [...new Set(data.scatter_data.map(d => d.cluster))];
    
    const scatterDatasets = clusters.map(clusterId => ({
        label: `Cluster ${clusterId}`,
        data: data.scatter_data.filter(d => d.cluster === clusterId).map(d => ({
            x: d.x,
            y: d.y,
            merchant: d.merchant
        })),
        backgroundColor: clusterColors[clusterId % clusterColors.length],
        pointRadius: 6,
        pointHoverRadius: 8,
    }));

    return (
        <div className="space-y-6">
            {/* PCA Scatter Plot */}
            <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl backdrop-blur-sm">
                <div className="mb-6">
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                        <BrainCircuit className="w-5 h-5 text-indigo-400" />
                        K-Means Clustering & PCA
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">
                        Merchants grouped into {clusters.length} clusters and reduced to 2D space using Principal Component Analysis.
                    </p>
                </div>
                <div className="h-[400px] w-full flex items-center justify-center">
                    {loading ? (
                        <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
                    ) : data.scatter_data.length === 0 ? (
                        <p className="text-slate-500 text-sm">Not enough data to run clustering.</p>
                    ) : (
                        <Scatter 
                            data={{ datasets: scatterDatasets }} 
                            options={{
                                responsive: true,
                                maintainAspectRatio: false,
                                plugins: {
                                    legend: { labels: { color: '#cbd5e1' } },
                                    tooltip: {
                                        callbacks: {
                                            label: (ctx) => `${ctx.raw.merchant}`
                                        }
                                    }
                                },
                                scales: {
                                    x: { grid: { color: '#1e293b' }, ticks: { display: false } },
                                    y: { grid: { color: '#1e293b' }, ticks: { display: false } }
                                }
                            }} 
                        />
                    )}
                </div>
            </div>

            {/* Apriori Insights */}
            <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl backdrop-blur-sm">
                <div className="mb-6">
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                        <Lightbulb className="w-5 h-5 text-amber-400" />
                        Apriori Association Rules
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">
                        Discovering hidden spending patterns across categories.
                    </p>
                </div>
                {loading ? (
                    <div className="flex justify-center py-10">
                        <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
                    </div>
                ) : data.apriori_insights.length === 0 ? (
                    <p className="text-slate-500 text-sm text-center py-4">Not enough data to find associations.</p>
                ) : (
                    <div className="grid gap-3 md:grid-cols-2">
                        {data.apriori_insights.map((insight, idx) => (
                            <div key={idx} className="p-4 bg-slate-800/40 border border-slate-700/60 rounded-xl">
                                <h4 className="text-sm font-semibold text-white">{insight.rule}</h4>
                                <p className="text-xs text-slate-300 mt-1">{insight.result}</p>
                                <span className="inline-block mt-3 px-2 py-1 bg-amber-500/10 text-amber-300 text-[10px] rounded-md">
                                    {insight.confidence}% Confidence
                                </span>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}