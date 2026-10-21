import React, { useState } from 'react';
import { ArrowUpRight, Search, ShieldAlert, Pencil, Check, X } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

const PREDEFINED_CATEGORIES = [
  'Food & Dining',
  'Groceries & Essentials',
  'Shopping',
  'Travel & Fuel',
  'Bills & Utilities',
  'Entertainment & Media',
  'Healthcare & Medicine',
  'Education & Fees',
  'Peer Transfer',
  'General Expense',
];

export default function TransactionHistory({ transactions = [], onCategoryChanged }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [pendingCategory, setPendingCategory] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [localOverrides, setLocalOverrides] = useState({});

  const filteredTransactions = transactions.filter((tx) =>
    tx.merchant.toLowerCase().includes(searchTerm.toLowerCase()) ||
    tx.category.toLowerCase().includes(searchTerm.toLowerCase()) ||
    tx.date.includes(searchTerm)
  );

  const startEdit = (tx) => {
    setEditingId(tx.id);
    setPendingCategory(localOverrides[tx.id] || tx.category);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setPendingCategory('');
  };

  const saveEdit = async (tx) => {
    const trimmed = pendingCategory.trim();

    // Nothing to save — bail out
    if (!trimmed || trimmed === (localOverrides[tx.id] || tx.category)) {
      cancelEdit();
      return;
    }

    setIsSaving(true);
    try {
      const res = await fetch(`${API_BASE}/api/transaction/${tx.id}/category/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ transaction_id: tx.id, category: trimmed }),
      });

      // Read raw text first so we can catch HTML error pages
      const rawText = await res.text();
      let data;
      try {
        data = JSON.parse(rawText);
      } catch {
        throw new Error(`Server error ${res.status}. Check the Django terminal.`);
      }

      if (!res.ok || data.status === 'error') {
        throw new Error(data.message || data.error || `Server error ${res.status}`);
      }

      // ✅ Optimistic update — flip the badge instantly
      setLocalOverrides((prev) => ({ ...prev, [tx.id]: trimmed }));

      // Then refresh from server in background
      if (onCategoryChanged) {
        await onCategoryChanged();
      }
      cancelEdit();
    } catch (err) {
      console.error('Category update failed:', err);
      alert(`Could not update category: ${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl backdrop-blur-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            Recent Transactions
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-400 font-normal border border-slate-700/50">
              {filteredTransactions.length} records
            </span>
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Click the pencil icon to correct any miscategorized merchant — the system remembers your choice
          </p>
        </div>

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

      <div className="space-y-2.5 max-h-[420px] overflow-y-auto pr-2">
        {filteredTransactions.length > 0 ? (
          filteredTransactions.map((tx, idx) => {
            const isEditing = editingId === tx.id;
            return (
              <div
                key={tx.id || idx}
                className="flex items-center justify-between p-3.5 bg-slate-800/30 hover:bg-slate-800/60 border border-slate-800/80 hover:border-slate-700/80 rounded-xl transition duration-150"
              >
                <div className="flex flex-col gap-1 flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h4 className="text-sm font-semibold text-white tracking-wide truncate">
                      {tx.merchant}
                    </h4>
                    {tx.is_anomaly && (
                      <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 bg-rose-500/10 border border-rose-500/20 text-rose-400 font-medium rounded-full shrink-0">
                        <ShieldAlert className="w-3 h-3" /> Flagged
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2 text-xs text-slate-400">
                    {isEditing ? (
                      <>
                        <input
                          type="text"
                          list={`category-presets-${tx.id}`}
                          value={pendingCategory}
                          onChange={(e) => setPendingCategory(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') { e.preventDefault(); saveEdit(tx); }
                            else if (e.key === 'Escape') { e.preventDefault(); cancelEdit(); }
                          }}
                          placeholder="Type or pick a category..."
                          className="bg-slate-900 text-white text-xs px-2.5 py-1 rounded-md border border-indigo-500/60 focus:outline-none focus:border-indigo-400 w-56"
                          autoFocus
                        />
                        <datalist id={`category-presets-${tx.id}`}>
                          {PREDEFINED_CATEGORIES.map((c) => (
                            <option key={c} value={c} />
                          ))}
                        </datalist>
                        <button
                          onClick={() => saveEdit(tx)}
                          disabled={isSaving}
                          className="p-1 bg-emerald-600/20 hover:bg-emerald-600/40 border border-emerald-500/40 text-emerald-400 rounded-md disabled:opacity-50"
                          title="Save"
                        >
                          <Check className="w-3 h-3" />
                        </button>
                        <button
                          onClick={cancelEdit}
                          disabled={isSaving}
                          className="p-1 bg-slate-700/40 hover:bg-slate-700/80 border border-slate-600 text-slate-300 rounded-md disabled:opacity-50"
                          title="Cancel"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          onClick={() => startEdit(tx)}
                          className="group flex items-center gap-1.5 px-2 py-0.5 text-[11px] font-medium text-indigo-300 bg-indigo-950/60 hover:bg-indigo-900/80 border border-indigo-800/40 rounded-md transition"
                          title="Click to re-categorize"
                        >
                          {localOverrides[tx.id] || tx.category}
                          <Pencil className="w-2.5 h-2.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                        </button>
                        <span>•</span>
                        <span>{tx.date}</span>
                      </>
                    )}
                  </div>
                </div>

                <div className="text-right shrink-0">
                  <p className="text-sm font-bold text-slate-100 flex items-center justify-end gap-1">
                    - ₹{Number(tx.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    <ArrowUpRight className="w-3.5 h-3.5 text-rose-400" />
                  </p>
                  <p className="text-[11px] text-emerald-400 font-medium mt-0.5">
                    Debited via UPI
                  </p>
                </div>
              </div>
            );
          })
        ) : (
          <div className="py-12 text-center text-slate-500 text-xs">
            No transactions found matching your criteria.
          </div>
        )}
      </div>
    </div>
  );
}