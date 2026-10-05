import React from 'react';

export default function AnomalyTable({ anomalies }) {
  return (
    <div className="lg:col-span-7 p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl backdrop-blur-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-base font-bold text-white">Flagged Suspicious Transactions</h3>
          <p className="text-xs text-slate-400">Outliers that deviate significantly from standard baseline spend</p>
        </div>
        <span className="px-3 py-1 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-semibold rounded-full">
          Isolation Forest Flags
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-slate-300">
          <thead className="bg-slate-800/50 text-slate-400 text-xs uppercase border-b border-slate-800">
            <tr>
              <th className="py-3 px-4">Merchant</th>
              <th className="py-3 px-4">Date</th>
              <th className="py-3 px-4">Amount</th>
              <th className="py-3 px-4">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {anomalies && anomalies.length > 0 ? (
              anomalies.map((item, index) => (
                <tr key={index} className="hover:bg-slate-800/30">
                  <td className="py-3 px-4 font-medium text-white">{item.Merchant || item.merchant || 'UNKNOWN'}</td>
                  <td className="py-3 px-4 text-xs text-slate-400">{item.Date || item.date}</td>
                  <td className="py-3 px-4 text-rose-400 font-semibold">
                    ₹{Number(item.Amount || item.amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </td>
                  <td className="py-3 px-4">
                    <span className="px-2 py-0.5 bg-rose-500/10 whitespace-nowrap inline-block text-rose-400 border border-rose-500/20 text-xs rounded-md">
                      Impulse Risk
                    </span>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="4" className="py-4 px-4 text-center text-xs text-slate-500">
                  No unusual transactions flagged in this dataset.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}