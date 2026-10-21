import React, { useState, useEffect, useRef } from 'react';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js';
import { Bar } from 'react-chartjs-2';
import { Loader2, TrendingUp } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export default function SpendingTrends() {
    const { token } = useAuth();
    const [granularity, setGranularity] = useState('month');
    const [chartData, setChartData] = useState({ labels: [], data: [] });
    const [loading, setLoading] = useState(true);
    
    const scrollRef = useRef(null);

    useEffect(() => {
        setLoading(true);
        fetch(`${API_BASE}/api/spending-trends/?granularity=${granularity}`, {
            headers: { 'Authorization': `Token ${token}` }
        })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    setChartData({ labels: data.labels, data: data.data });
                }
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setLoading(false);
            });
    }, [granularity, token]);

    useEffect(() => {
        if (!loading && scrollRef.current) {
            scrollRef.current.scrollLeft = scrollRef.current.scrollWidth;
        }
    }, [chartData, loading, granularity]);

    const data = {
        labels: chartData.labels,
        datasets: [
            {
                label: 'Total Spend (₹)',
                data: chartData.data,
                backgroundColor: 'rgba(99, 102, 241, 0.8)',
                hoverBackgroundColor: 'rgba(99, 102, 241, 1)',
                borderRadius: 6,
            },
        ],
    };

    // --- SHARED CONFIGURATION FOR PERFECT ALIGNMENT ---
    const sharedXAxis = {
        display: true,
        grid: { display: false },
        ticks: { 
            font: { size: 10 }, 
            maxRotation: 45, 
            minRotation: 45,
        },
        offset: true,
    };

    const sharedLayout = { padding: { bottom: 10 } };

    // LEFT CHART (Sticky Y-Axis)
    const yAxisOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { enabled: false } },
        scales: {
            x: { 
                ...sharedXAxis,
                ticks: { 
                    ...sharedXAxis.ticks,
                    color: 'transparent', // Hide text but keep space
                }, 
            }, 
            y: {
                position: 'left',
                beginAtZero: true,   
                min: 0,
                grid: { display: false },
                border: { display: false },
                ticks: { 
                    color: '#94a3b8', 
                    padding: 8, 
                    font: { size: 11 },
                    crossAlign: 'far',
                },
            },
        },
        layout: sharedLayout
    };

    const yAxisData = {
        labels: chartData.labels,
        datasets: [{
            ...data.datasets[0],
            backgroundColor: 'transparent', 
            hoverBackgroundColor: 'transparent',
            barPercentage: 1.0, 
            categoryPercentage: 1.0, 
        }]
    };

    // RIGHT CHART (Bars + Grid Lines)
    const mainChartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false },
            tooltip: {
                backgroundColor: '#1e293b', titleColor: '#f8fafc', bodyColor: '#cbd5e1',
                borderColor: '#334155', borderWidth: 1, padding: 10,
                callbacks: { label: (context) => ` ₹${context.raw.toLocaleString()}` },
            },
        },
        scales: {
            x: {
                ...sharedXAxis,
                ticks: { 
                    ...sharedXAxis.ticks,
                    color: '#94a3b8', 
                    autoSkip: true, 
                },
            },
            y: { 
                position: 'left',
                beginAtZero: true,   
                min: 0,
                ticks: { display: false }, // Hide numbers
                grid: { 
                    color: '#1e293b', 
                    drawTicks: false 
                },
                border: { display: false } 
            }, 
        },
        layout: sharedLayout
    };

    return (
        <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl backdrop-blur-sm min-h-[500px]">
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                        <TrendingUp className="w-5 h-5 text-indigo-400" />
                        Spending Trends
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">Visualize your cash flow over time</p>
                </div>

                <div className="flex bg-slate-800/80 p-1 rounded-xl border border-slate-700/80">
                    {[{ value: 'day', label: 'Daily' }, { value: 'month', label: 'Monthly' }, { value: 'year', label: 'Yearly' }].map((item) => (
                        <button
                            key={item.value}
                            onClick={() => setGranularity(item.value)}
                            className={`px-4 py-1.5 text-xs font-semibold rounded-lg transition ${
                                granularity === item.value ? 'bg-indigo-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'
                            }`}
                        >
                            {item.label}
                        </button>
                    ))}
                </div>
            </div>

            {loading ? (
                <div className="h-[350px] flex items-center justify-center">
                    <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
                </div>
            ) : chartData.labels.length === 0 ? (
                <div className="h-[350px] flex items-center justify-center">
                    <p className="text-slate-500 text-sm">No data available. Upload a CSV first.</p>
                </div>
            ) : (
                <div className="flex w-full pt-4">
                    
                    {/* FIXED LEFT Y-AXIS (Width 75px) */}
                    <div className="w-[75px] h-[350px] shrink-0 relative z-20 bg-slate-900/95">
                        <Bar data={yAxisData} options={yAxisOptions} />
                    </div>

                    {/* SCROLLABLE RIGHT CHART */}
                    <div 
                        ref={scrollRef}
                        className="flex-1 overflow-x-auto overflow-y-hidden custom-scrollbar relative"
                    >
                        <div
                            className="h-[350px]"
                            style={{
                                minWidth: granularity === 'day' && chartData.labels.length > 15
                                    ? `${chartData.labels.length * 55}px`
                                    : '100%'
                            }}
                        >
                            <Bar data={data} options={mainChartOptions} />
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}