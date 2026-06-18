// src/components/intro/IntroPanel.jsx
// Static greeting + sample data description block. Renders data
// returned by the public /api/intro endpoint.

import React, { useEffect, useState, useCallback } from 'react';
import {
  Database, BarChart3, FileText, PlayCircle, RefreshCw, AlertTriangle, ChevronDown, ChevronUp,
} from 'lucide-react';
import useAppStore from '../../store/useAppStore';

function formatCount(n) {
  if (n === null || n === undefined) return '0';
  return Number(n).toLocaleString();
}

function SampleRow({ name, label, source, description, columns, rowCount, onTellMe, isLoading }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 transition-colors">
      <div className="px-4 py-3 flex items-start gap-3">
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${
          source === 'db'
            ? 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-300'
            : 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-300'
        }`}>
          {source === 'db' ? <Database size={18} /> : <FileText size={18} />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <p className="text-sm font-semibold text-gray-800 dark:text-gray-100 truncate">
              {label}
            </p>
            <span className={`text-[10px] font-medium uppercase tracking-wider px-2 py-0.5 rounded-full ${
              source === 'db'
                ? 'bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300'
                : 'bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300'
            }`}>
              {source === 'db' ? 'Database' : 'Sample file'}
            </span>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 leading-relaxed">
            {description}
          </p>
          <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-gray-500 dark:text-gray-400">
            {rowCount > 0 && (
              <span className="inline-flex items-center gap-1">
                <BarChart3 size={12} />
                {formatCount(rowCount)} rows
              </span>
            )}
            {columns && columns.length > 0 && (
              <span className="inline-flex items-center gap-1">
                <FileText size={12} />
                {columns.length} columns
              </span>
            )}
            <button
              type="button"
              onClick={() => setOpen((v) => !v)}
              className="ml-auto inline-flex items-center gap-1 text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
            >
              {open ? 'Hide columns' : 'Show columns'}
              {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>
          </div>
          {open && columns && columns.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {columns.map((c) => (
                <span key={c} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                  {c}
                </span>
              ))}
            </div>
          )}
          <div className="mt-3">
            <button
              type="button"
              onClick={() => onTellMe(name)}
              disabled={isLoading}
              className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 dark:disabled:bg-blue-800 text-white transition-colors disabled:cursor-not-allowed"
            >
              {isLoading ? <RefreshCw size={12} className="animate-spin" /> : <PlayCircle size={12} />}
              Tell me about this data
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function IntroPanel() {
  const intro = useAppStore((s) => s.intro);
  const serverStatus = useAppStore((s) => s.serverStatus);
  const loadIntro = useAppStore((s) => s.loadIntro);
  const isLoading = useAppStore((s) => s.isLoading);
  const tellMeAboutSample = useAppStore((s) => s.tellMeAboutSample);

  const [retrying, setRetrying] = useState(false);

  // NOTE: hooks below are declared in a fixed order so the hook count
  // never changes between renders. The "early return" for the loading
  // state is moved AFTER all hook calls.

  const reload = useCallback(async () => {
    setRetrying(true);
    try { await loadIntro(); } finally { setRetrying(false); }
  }, [loadIntro]);

  const handleTellMe = useCallback(async () => {
    try { await tellMeAboutSample(); } catch { /* surfaced via store */ }
  }, [tellMeAboutSample]);

  useEffect(() => {
    if (!intro) loadIntro();
  }, [intro, loadIntro]);

  if (!intro) {
    return (
      <div className="flex flex-col items-center justify-center text-gray-400 dark:text-gray-500 py-12">
        <RefreshCw size={28} className="animate-spin mb-3 opacity-60" />
        <p className="text-sm font-medium">Loading system information...</p>
        <p className="text-xs mt-1">This can take up to a minute on first visit while the backend warms up.</p>
      </div>
    );
  }

  const title = intro?.intro?.title || 'Steam Game Data Analyst';
  const tagline = intro?.intro?.tagline || '';
  const systemNotes = intro?.intro?.system_notes || [];
  const howTo = intro?.intro?.how_to_use || [];
  const futureWork = intro?.intro?.future_work || [];

  const local = intro?.sample_data?.local;
  const db = intro?.sample_data?.database;
  const dbAvailable = !!db?.available;
  const dbError = db?.error;
  const dbCounts = db?.row_counts || {};

  return (
    <div className="space-y-6 text-gray-700 dark:text-gray-200">
      {/* Greeting */}
      <section>
        <h2 className="text-xl font-bold text-gray-900 dark:text-gray-50 mb-1">
          {title}
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
          {tagline}
        </p>
      </section>

      {/* System notes (free-tier warning, etc.) */}
      {systemNotes.length > 0 && (
        <section className="border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20 rounded-xl p-4">
          <div className="flex items-start gap-2 mb-2">
            <AlertTriangle size={16} className="text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
            <h3 className="text-sm font-semibold text-amber-800 dark:text-amber-300">
              System notes
            </h3>
          </div>
          <ul className="space-y-1.5 text-xs text-amber-700 dark:text-amber-300 list-disc list-inside leading-relaxed">
            {systemNotes.map((n, i) => <li key={i}>{n}</li>)}
          </ul>
          {serverStatus?.free_tier_notes && (
            <p className="mt-3 text-xs text-amber-700 dark:text-amber-300 leading-relaxed">
              {serverStatus.free_tier_notes}
            </p>
          )}
        </section>
      )}

      {/* Sample data blocks */}
      <section>
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-3 uppercase tracking-wider">
          Sample data already loaded
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {local && (
            <SampleRow
              name={local.name}
              label={local.title}
              source="sample"
              description={local.description}
              columns={local.columns || []}
              rowCount={local._rowCount || 0}
              onTellMe={handleTellMe}
              isLoading={isLoading}
            />
          )}

          {db && db.tables?.map((t) => {
            const alias = t.alias;
            const count = dbCounts?.[alias] || 0;
            const cols = (db.columns && db.columns[alias]) || [];
            return (
              <SampleRow
                key={t.name}
                name={t.name}
                label={t.description?.split('.')[0] || t.name}
                source="db"
                description={t.description}
                columns={cols}
                rowCount={count}
                onTellMe={handleTellMe}
                isLoading={isLoading}
              />
            );
          })}
        </div>

        {/* DB error banner */}
        {db && !dbAvailable && dbError && (
          <div className="mt-3 text-xs text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3">
            Database preview is unavailable: {dbError}. The backend can still
            answer questions using the bundled sample file.
          </div>
        )}

        <div className="mt-3 flex items-center justify-between">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Both samples are loaded automatically. Use the button above to send a pre-filled prompt to the backend.
          </p>
          <button
            type="button"
            onClick={reload}
            disabled={retrying}
            className="inline-flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 disabled:opacity-50"
          >
            <RefreshCw size={12} className={retrying ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </section>

      {/* How to use */}
      {howTo.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-3 uppercase tracking-wider">
            How to use
          </h3>
          <ol className="space-y-1.5 text-sm text-gray-600 dark:text-gray-400 list-decimal list-inside leading-relaxed">
            {howTo.map((line, i) => <li key={i}>{line}</li>)}
          </ol>
        </section>
      )}

      {/* Future work */}
      {futureWork.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-3 uppercase tracking-wider">
            Future work
          </h3>
          <ul className="space-y-1.5 text-sm text-gray-600 dark:text-gray-400 list-disc list-inside leading-relaxed">
            {futureWork.map((line, i) => <li key={i}>{line}</li>)}
          </ul>
        </section>
      )}
    </div>
  );
}
