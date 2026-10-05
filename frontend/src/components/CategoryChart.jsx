import React, { useState } from 'react';
import { Doughnut } from 'react-chartjs-2';
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';

ChartJS.register(ArcElement, Tooltip, Legend);

// Preset vibrant palette for dynamic AI categories
const COLOR_PALETTE = [
  '#6366f1', '#ec4899', '#10b981', '#f59e0b', '#8b5cf6',
  '#06b6d4', '#f43f5e', '#3b82f6', '#14b8a6', '#a855f7',
  '#eab308', '#64748b', '#06b6d4', '#f97316'
];

export default function CategoryChart({ categories = {} }) {
  const allLabels = Object.keys(categories);
  const allDataValues = Object.values(categories);
  const totalSpend = allDataValues.reduce((sum, val) => sum + val, 0);

  // Track which categories the user has toggled off
  const [hiddenCategories, setHiddenCategories] = useState(new Set());

  const toggleCategory = (label) => {
    setHiddenCategories(prev => {
      const newSet = new Set(prev);
      if (newSet.has(label)) {
        newSet.delete(label);
      } else {
        newSet.add(label);
      }
      return newSet;
    });
  };

  // Filter out hidden categories before passing data to the chart
  const chartLabels = [];
  const chartDataValues = [];
  const chartColors = [];

  allLabels.forEach((label, index) => {
    if (!hiddenCategories.has(label)) {
      chartLabels.push(label);
      chartDataValues.push(allDataValues[index]);
      chartColors.push(COLOR_PALETTE[index % COLOR_PALETTE.length]);
    }
  });

  const data = {
    labels: chartLabels.length > 0 ? chartLabels : ['No Data'],
    datasets: [
      {
        data: chartDataValues.length > 0 ? chartDataValues : [1],
        backgroundColor: chartDataValues.length > 0 ? chartColors : ['#334155'],
        borderColor: '#0f172a',
        borderWidth: 2,
        hoverOffset: 6,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false, // Keep native legend disabled to prevent overflow
      },
      tooltip: {
        backgroundColor: '#1e293b',
        titleColor: '#f8fafc',
        bodyColor: '#cbd5e1',
        borderColor: '#334155',
        borderWidth: 1,
        padding: 10,
        callbacks: {
          label: (context) => {
            const val = context.raw || 0;
            if (chartLabels.length === 0) return ' No Data';
            return ` ₹${Number(val).toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
          },
        },
      },
    },
    cutout: '70%',
    animation: {
      animateScale: true,
      animateRotate: true
    }
  };

  return (
    <div className="lg:col-span-5 p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl backdrop-blur-sm flex flex-col justify-between min-h-[420px]">
      <div>
        <h3 className="text-lg font-bold text-white">Expense Categorization</h3>
        <p className="text-xs text-slate-400 mt-0.5">Dynamic AI categorization powered by Gemini</p>
      </div>

      <div className="relative h-48 my-3 flex items-center justify-center">
        <Doughnut data={data} options={options} />
      </div>

      {/* Interactive Custom Scrollable Legend */}
      <div className="max-h-36 overflow-y-auto pr-1 space-y-1.5 border-t border-slate-800/80 pt-3">
        {allLabels.length > 0 ? (
          allLabels.map((label, idx) => {
            const amount = allDataValues[idx] || 0;
            const percentage = totalSpend > 0 ? ((amount / totalSpend) * 100).toFixed(1) : 0;
            const isHidden = hiddenCategories.has(label);
            
            return (
              <div 
                key={label} 
                onClick={() => toggleCategory(label)}
                className={`flex items-center justify-between text-xs py-1 px-2 rounded-lg cursor-pointer transition-all duration-200 
                  ${isHidden ? 'opacity-40 grayscale hover:bg-slate-800/40' : 'hover:bg-slate-800/60'}`}
              >
                <div className="flex items-center gap-2 truncate pr-2">
                  <span
                    className="w-2.5 h-2.5 rounded-full shrink-0 transition-colors"
                    style={{ backgroundColor: isHidden ? '#475569' : COLOR_PALETTE[idx % COLOR_PALETTE.length] }}
                  />
                  <span className={`font-medium truncate transition-all ${isHidden ? 'text-slate-500 line-through' : 'text-slate-300'}`}>
                    {label}
                  </span>
                </div>
                <div className="text-right shrink-0">
                  <span className={`font-bold transition-all ${isHidden ? 'text-slate-500 line-through' : 'text-slate-200'}`}>
                    ₹{Number(amount).toLocaleString()}
                  </span>
                  <span className="text-[10px] text-slate-500 ml-1.5">({percentage}%)</span>
                </div>
              </div>
            );
          })
        ) : (
          <div className="text-center text-xs text-slate-500 py-2">No category data available</div>
        )}
      </div>
    </div>
  );
}