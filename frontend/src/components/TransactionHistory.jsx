import React, { useState } from 'react';
import { ArrowUpRight, Search, ShieldAlert } from 'lucide-react';

export default function TransactionHistory({ transactions = [] }) {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredTransactions = transactions.filter((tx) =>
    tx.merchant.toLowerCase().includes(searchTerm.toLowerCase()) ||
    tx.category.toLowerCase().includes(searchTerm.toLowerCase()) ||
    tx.date.includes(searchTerm)
  );

  return (
    <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl backdrop-blur-sm">
      {/* Header & Search Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            Recent Transactions
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-400 font-normal border border-slate-700/50">
              {filteredTransactions.length} records
            </span>
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">UPI history parsed directly from uploaded statements</p>
        </div>

        {/* Search Bar */}
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search merchant, category..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9 pr-4 py-2 bg-slate-800/80 text-white text-xs rounded-xl border border-slate-700/80 focus:outline-none focus:border-indigo-500 w-full sm:w-64 placeholder:text-slate-500"
          />
        </div>
      </div>

      {/* Transaction Feed */}
      <div className="space-y-2.5 max-h-[420px] overflow-y-auto pr-2">
        {filteredTransactions.length > 0 ? (
          filteredTransactions.map((tx, idx) => (
            <div
              key={tx.id || idx}
              className="flex items-center justify-between p-3.5 bg-slate-800/30 hover:bg-slate-800/60 border border-slate-800/80 hover:border-slate-700/80 rounded-xl transition duration-150"
            >
              {/* Merchant Details & Dynamic Category Badge */}
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <h4 className="text-sm font-semibold text-white tracking-wide">
                    {tx.merchant}
                  </h4>
                  {tx.is_anomaly && (
                    <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 bg-rose-500/10 border border-rose-500/20 text-rose-400 font-medium rounded-full">
                      <ShieldAlert className="w-3 h-3" /> Flagged
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2 text-xs text-slate-400">
                  <span className="px-2 py-0.5 text-[11px] font-medium text-indigo-300 bg-indigo-950/60 border border-indigo-800/40 rounded-md">
                    {tx.category}
                  </span>
                  <span>•</span>
                  <span>{tx.date}</span>
                </div>
              </div>

              {/* Transaction Amount */}
              <div className="text-right">
                <p className="text-sm font-bold text-slate-100 flex items-center justify-end gap-1">
                  - ₹{Number(tx.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  <ArrowUpRight className="w-3.5 h-3.5 text-rose-400" />
                </p>
                <p className="text-[11px] text-emerald-400 font-medium mt-0.5">
                  Debited via UPI
                </p>
              </div>
            </div>
          ))
        ) : (
          <div className="py-12 text-center text-slate-500 text-xs">
            No transactions found matching your criteria.
          </div>
        )}
      </div>
    </div>
  );
}