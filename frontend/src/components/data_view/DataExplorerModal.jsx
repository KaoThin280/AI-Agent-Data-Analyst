import React, { useState, useEffect } from 'react';
import { X, Loader2, AlertTriangle } from 'lucide-react';
import { getTableData } from '../../services/api';
import DataExplorer from './DataExplorer';

export default function DataExplorerModal({ fileName, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!fileName) return;
    setLoading(true);
    setError(null);

    getTableData(fileName)
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load table data:', err);
        setError(err?.response?.data?.detail || err.message || 'Failed to load data.');
        setLoading(false);
      });
  }, [fileName]);

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
      role="presentation"
    >
      <div 
        className="relative max-h-[90vh] w-full max-w-6xl overflow-auto rounded-xl bg-white shadow-2xl dark:bg-gray-900"
        onClick={(e) => e.stopPropagation()}
      >
        {/* ── Header ──────────────────────────────────────────────── */}
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-gray-200 bg-white px-6 py-4 dark:border-gray-700 dark:bg-gray-900">
          <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
            Data Explorer — {fileName}
          </h2>
          <button
            onClick={onClose}
            className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300"
          >
            <X size={20} />
          </button>
        </div>

        {/* ── Content ─────────────────────────────────────────────── */}
        <div className="p-6">
          {loading && (
            <div className="flex items-center justify-center py-16 text-gray-400">
              <Loader2 className="mr-2 animate-spin" size={24} />
              Loading data…
            </div>
          )}

          {error && (
            <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20">
              <AlertTriangle className="mt-0.5 shrink-0 text-red-500" size={20} />
              <div>
                <p className="font-medium text-red-700 dark:text-red-400">Failed to load data</p>
                <p className="text-sm text-red-600 dark:text-red-300">{error}</p>
              </div>
            </div>
          )}

          {data && !loading && !error && (
            <DataExplorer
              fileName={fileName}
              rows={data?.data || []}
              columns={data?.columns ? Object.keys(data.columns) : []}
            />
          )}
        </div>
      </div>
    </div>
  );
}