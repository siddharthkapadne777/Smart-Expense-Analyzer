import React from 'react';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler } from 'chart.js';
import { Line } from 'react-chartjs-2';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler);

export default function ForecastChart({ forecastDataArray }) {
  const forecastData = {
    labels: ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5', 'Day 6', 'Day 7'],
    datasets: [{
      label: '7-Day Forecasted Spend (₹)',
      data: forecastDataArray || [0, 0, 0, 0, 0, 0, 0],
      borderColor: '#6366F1',
      backgroundColor: 'rgba(99, 102, 241, 0.1)',
      fill: true,
      tension: 0.4,
    }]
  };

  return (
    <div className="lg:col-span-7 p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl backdrop-blur-sm flex flex-col justify-between">
      <div>
        <h3 className="text-base font-bold text-white mb-1">7-Day Spending Trend & Prediction</h3>
        <p className="text-xs text-slate-400 mb-6">Proactive time-series analysis for daily budget management</p>
      </div>
      <div className="h-[260px] w-full">
        <Line data={forecastData} options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { color: '#1e293b' }, ticks: { color: '#94a3b8' } }, y: { grid: { color: '#1e293b' }, ticks: { color: '#94a3b8' } } } }} />
      </div>
    </div>
  );
}