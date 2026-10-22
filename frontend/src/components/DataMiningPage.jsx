import React, { useState, useEffect } from 'react';
import { Scatter } from 'react-chartjs-2';
import { Chart as ChartJS, LinearScale, PointElement, Tooltip, Legend } from 'chart.js';
import { Loader2, BrainCircuit, Lightbulb, TrendingUp, Sparkles, Layers, Calendar } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
// Agar aapka FilterBar component reusable hai, toh usko yahan import kar sakte hain
// import FilterBar from './FilterBar'; 

ChartJS.register(LinearScale, PointElement, Tooltip, Legend);
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

const CLUSTER_COLORS = [
    '#6366f1', '#ec4899', '#10b981', '#f59e0b', '#8b5cf6', 
    '#06b6d4', '#f43f5e', '#3b82f6', '#14b8a6', '#a855f7'
];

export default function DataMiningPage() {
    const { token } = useAuth();
    
    // Date Filters State
    const [timeRange, setTimeRange] = useState('month'); // 'month', 'year', 'all', 'custom'
    const [startDate, setStartDate] = useState('');
    const [endDate, setEndDate] = useState('');

    const [data, setData] = useState({ scatter_data: [], apriori_insights: [] });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        setLoading(true);
        
        let url = `${API_BASE}/api/data-mining/?range=${timeRange}`;
        if (timeRange === 'custom' && startDate && endDate) {
            url += `&start_date=${startDate}&end_date=${endDate}`;
        }

        fetch(url, {
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
    }, [token, timeRange, startDate, endDate]);

    const clusters = [...new Set(data.scatter_data.map(d => d.cluster))];
    
    const scatterDatasets = clusters.map((clusterId) => ({
        label: `Cluster ${clusterId + 1}`,
        data: data.scatter_data.filter(d => d.cluster === clusterId).map(d => {
            const jitter = () => (Math.random() - 0.5) * 0.5; 
            return {
                x: d.x + jitter(),
                y: d.y + jitter(),
                merchant: d.merchant
            };
        }),
        backgroundColor: CLUSTER_COLORS[clusterId % CLUSTER_COLORS.length],
        borderColor: 'rgba(255,255,255,0.4)',
        borderWidth: 1.5,
        pointRadius: 6,       
        pointHoverRadius: 10,
        pointHitRadius: 15,   
    }));

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { position: 'top', labels: { color: '#cbd5e1', usePointStyle: true, padding: 20, font: { size: 12 } } },
            tooltip: { backgroundColor: '#1e293b', titleColor: '#f8fafc', bodyColor: '#cbd5e1', borderColor: '#334155', borderWidth: 1, padding: 12, displayColors: false, callbacks: { label: (ctx) => `Merchant: ${ctx.raw.merchant}`, title: () => 'Merchant Cluster' } }
        },
        scales: { x: { grid: { color: '#1e293b', drawBorder: false }, ticks: { display: false } }, y: { grid: { color: '#1e293b', drawBorder: false }, ticks: { display: false } } }
    };

    const groupedClusterDetails = clusters.map(clusterId => {
        const items = data.scatter_data.filter(d => d.cluster === clusterId);
        const uniqueMerchants = [...new Set(items.map(item => item.merchant))];
        const totalSpend = items.reduce((sum, item) => sum + item.amount, 0);
        return { id: clusterId, color: CLUSTER_COLORS[clusterId % CLUSTER_COLORS.length], merchants: uniqueMerchants, totalSpend };
    });

    return (
        <div className="space-y-6">
            {/* TOP TOOLBAR WITH TIME FILTERS */}
            <div className="flex flex-wrap items-center justify-between gap-4 p-4 bg-slate-900/40 border border-slate-800/80 rounded-2xl">
                <div className="flex items-center gap-2 text-slate-300">
                    <Calendar className="w-4 h-4 text-indigo-400" />
                    <span className="text-xs font-semibold uppercase tracking-wider">Filter Data By</span>
                </div>
                
                <div className="flex flex-wrap items-center gap-3">
                    {/* Custom Date Pickers */}
                    {timeRange === 'custom' && (
                        <div className="flex items-center gap-2 bg-slate-800/60 p-1.5 rounded-xl border border-slate-700/80">
                            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="bg-slate-800 text-white px-2.5 py-1 rounded-lg border border-slate-700 text-xs focus:outline-none focus:border-indigo-500 [color-scheme:dark]" />
                            <span className="text-slate-400 text-xs font-medium">to</span>
                            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="bg-slate-800 text-white px-2.5 py-1 rounded-lg border border-slate-700 text-xs focus:outline-none focus:border-indigo-500 [color-scheme:dark]" />
                        </div>
                    )}
                    
                    {/* Range Dropdown */}
                    <select 
                        value={timeRange} 
                        onChange={(e) => setTimeRange(e.target.value)}
                        className="bg-slate-800/80 text-slate-200 text-sm px-3.5 py-2 rounded-xl border border-slate-700/80 focus:outline-none focus:border-indigo-500"
                    >
                        <option value="month">Last 30 Days</option>
                        <option value="year">Last 1 Year</option>
                        <option value="all">All Time</option>
                        <option value="custom">Custom Range</option>
                    </select>
                </div>
            </div>

            {/* PCA Scatter Plot */}
            <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl backdrop-blur-sm">
                <div className="mb-6">
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                        <BrainCircuit className="w-5 h-5 text-indigo-400" />
                        K-Means Clustering & PCA Graph
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">
                        Merchants reduced to 2D space using Principal Component Analysis.
                    </p>
                </div>
                
                <div className="h-[400px] w-full flex items-center justify-center">
                    {loading ? (
                        <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
                    ) : data.scatter_data.length === 0 ? (
                        <p className="text-slate-500 text-sm">Not enough data to run clustering for this period.</p>
                    ) : (
                        <Scatter data={{ datasets: scatterDatasets }} options={chartOptions} />
                    )}
                </div>
            </div>

            {/* CLUSTER DETAILS LIST */}
            <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl backdrop-blur-sm">
                <div className="mb-6">
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                        <Layers className="w-5 h-5 text-emerald-400" />
                        Cluster Details
                    </h3>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {groupedClusterDetails.map((cluster, idx) => (
                        <div key={idx} className="bg-slate-800/40 border border-slate-700/60 rounded-xl overflow-hidden">
                            <div className="px-4 py-3 border-b border-slate-700/60 flex items-center justify-between" style={{ backgroundColor: `${cluster.color}15` }}>
                                <div className="flex items-center gap-2">
                                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: cluster.color }}></div>
                                    <h4 className="text-sm font-bold text-white">Cluster {cluster.id + 1}</h4>
                                </div>
                                <span className="text-xs font-semibold text-slate-300">₹{cluster.totalSpend.toLocaleString()}</span>
                            </div>
                            <div className="p-4 max-h-[150px] overflow-y-auto custom-scrollbar">
                                <ul className="space-y-2">
                                    {cluster.merchants.map((merchant, i) => (
                                        <li key={i} className="text-xs text-slate-300 flex items-start gap-2">
                                            <span className="text-slate-500 mt-0.5">•</span>
                                            <span className="truncate">{merchant}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Apriori Insights */}
            <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl backdrop-blur-sm">
                <div className="mb-6">
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                        <Lightbulb className="w-5 h-5 text-amber-400" />
                        Apriori Association Rules
                    </h3>
                </div>
                
                {loading ? (
                    <div className="flex justify-center py-10"><Loader2 className="w-6 h-6 text-indigo-500 animate-spin" /></div>
                ) : data.apriori_insights.length === 0 ? (
                    <p className="text-slate-500 text-sm text-center py-4">Not enough data to find associations for this period.</p>
                ) : (
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                        {data.apriori_insights.map((insight, idx) => (
                            <div key={idx} className="p-5 bg-slate-800/40 border border-slate-700/60 rounded-xl hover:border-amber-500/30 transition group relative overflow-hidden">
                                <Sparkles className="absolute -right-4 -top-4 w-20 h-20 text-slate-700/20 group-hover:text-amber-500/10 transition" />
                                <div className="flex items-start gap-3 relative z-10">
                                    <div className="p-2 bg-amber-500/10 rounded-lg shrink-0"><TrendingUp className="w-5 h-5 text-amber-400" /></div>
                                    <div>
                                        <h4 className="text-sm font-semibold text-white mb-2 leading-tight">{insight.rule}</h4>
                                        <p className="text-xs text-slate-300 mb-3">{insight.result}</p>
                                        <div className="inline-block px-2.5 py-1 bg-amber-500/10 border border-amber-500/20 text-amber-300 text-[11px] rounded-md font-mono font-bold">{insight.confidence}% Confidence</div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}