import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';

// --- Custom Styled Dropdown Component ---
const CustomDropdown = ({ value, options, onChange, minWidth = 'w-44' }) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  // Close dropdown when clicking outside of it
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const selectedOption = options.find((opt) => opt.value === value) || options[0];

  return (
    <div className={`relative ${minWidth}`} ref={dropdownRef}>
      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between w-full bg-slate-800/80 text-slate-200 text-sm px-3.5 py-2 rounded-xl border border-slate-700/80 hover:border-slate-600 focus:outline-none focus:border-indigo-500 transition-colors"
      >
        <span className="truncate pr-2">{selectedOption?.label}</span>
        <ChevronDown 
          className={`w-4 h-4 text-slate-400 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} 
        />
      </button>

      {/* Floating Menu */}
      {isOpen && (
        <div className="absolute z-50 w-full mt-1.5 bg-[#1e293b] border border-slate-700 rounded-lg shadow-2xl overflow-hidden py-1">
          <div className="max-h-60 overflow-y-auto custom-scrollbar">
            {options.map((opt) => (
              <div
                key={opt.value}
                onClick={() => {
                  onChange(opt.value);
                  setIsOpen(false);
                }}
                className={`px-3.5 py-2 text-sm cursor-pointer transition-colors ${
                  value === opt.value
                    ? 'bg-blue-600 text-white' // The exact blue highlight from your screenshot
                    : 'text-slate-300 hover:bg-slate-700/80'
                }`}
              >
                {opt.label}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// --- Main FilterBar Component ---
export default function FilterBar({ 
  timeRange, 
  setTimeRange, 
  selectedCategory, 
  setSelectedCategory,
  categories = {},
  startDate,
  setStartDate,
  endDate,
  setEndDate
}) {
  // Format options for the Custom Dropdown
  const timeOptions = [
    { value: 'all', label: 'All Time' },
    { value: 'week', label: 'Last 7 Days' },
    { value: 'month', label: 'Last 30 Days' },
    { value: 'year', label: 'Last Year' },
    { value: 'custom', label: 'Custom Range' },
  ];

  const categoryOptions = [
    { value: 'all', label: 'All Categories' },
    ...Object.keys(categories).map((cat) => ({ value: cat, label: cat }))
  ];

  return (
    <div className="flex flex-wrap items-center justify-between gap-4 p-4 bg-slate-900/40 border border-slate-800/80 rounded-2xl">
      <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
        Dashboard Filters
      </span>

      <div className="flex flex-wrap items-center gap-3">
        {/* Custom Date Pickers (Shown only when 'custom' is selected) */}
        {timeRange === 'custom' && (
          <div className="flex items-center gap-2 bg-slate-800/60 p-1.5 rounded-xl border border-slate-700/80">
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="bg-slate-800 text-white px-2.5 py-1 rounded-lg border border-slate-700 text-xs focus:outline-none focus:border-indigo-500 [color-scheme:dark]"
            />
            <span className="text-slate-400 text-xs font-medium">to</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="bg-slate-800 text-white px-2.5 py-1 rounded-lg border border-slate-700 text-xs focus:outline-none focus:border-indigo-500 [color-scheme:dark]"
            />
          </div>
        )}

        {/* Custom Time Range Dropdown */}
        <CustomDropdown 
          value={timeRange} 
          options={timeOptions} 
          onChange={setTimeRange} 
          minWidth="w-40"
        />

        {/* Custom Dynamic Category Dropdown */}
        <CustomDropdown 
          value={selectedCategory} 
          options={categoryOptions} 
          onChange={setSelectedCategory} 
          minWidth="w-56"
        />
      </div>
    </div>
  );
}