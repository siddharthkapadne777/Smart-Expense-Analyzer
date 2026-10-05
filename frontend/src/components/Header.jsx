import React from 'react';
import { Upload } from 'lucide-react';

export default function Header({ file, isAnalyzing, handleFileChange, handleUpload }) {
  return (
    <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-6">
      <div>
        <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
          Financial Intelligence Dashboard
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Upload raw UPI transaction CSVs to generate predictive AI insights.
        </p>
      </div>

      <div className="flex items-center gap-3 bg-slate-900 border border-slate-800 p-2 rounded-2xl shadow-inner">
        <input
          type="file"
          accept=".csv"
          id="csv-input"
          className="hidden"
          onChange={handleFileChange}
        />
        <label
          htmlFor="csv-input"
          className="cursor-pointer flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium rounded-xl transition border border-slate-700"
        >
          <Upload className="w-4 h-4 text-indigo-400" />
          {file ? file.name.slice(0, 15) + '...' : 'Select UPI CSV'}
        </label>
        <button
          onClick={handleUpload}
          disabled={!file || isAnalyzing}
          className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-semibold rounded-xl shadow-lg shadow-indigo-600/30 transition flex items-center gap-2"
        >
          {isAnalyzing ? 'Analyzing...' : 'Process CSV'}
        </button>
      </div>
    </header>
  );
}