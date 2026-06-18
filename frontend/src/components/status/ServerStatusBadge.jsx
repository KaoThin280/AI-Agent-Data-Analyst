// src/components/status/ServerStatusBadge.jsx
// Compact connection status badge for the topbar.
// Pings /api/status periodically so the user can see when the
// backend has finished waking up after being idle.

import React, { useEffect, useRef, useState } from 'react';
import { Activity, Loader2, CheckCircle2, AlertTriangle, Info } from 'lucide-react';
import useAppStore from '../../store/useAppStore';

const STATE_LABELS = {
  ready:   { label: 'Connected',    tone: 'ok',    icon: CheckCircle2 },
  warming: { label: 'Connecting...', tone: 'warn', icon: Loader2 },
  error:   { label: 'Unreachable',  tone: 'error', icon: AlertTriangle },
  unknown: { label: 'Checking...',  tone: 'warn', icon: Loader2 },
};

export default function ServerStatusBadge() {
  const serverStatus = useAppStore((s) => s.serverStatus);
  const checkServerStatus = useAppStore((s) => s.checkServerStatus);
  const isCheckingStatus = useAppStore((s) => s.isCheckingStatus);
  const [open, setOpen] = useState(false);
  const containerRef = useRef(null);

  // Poll every 15 s while warming, every 60 s when connected.
  useEffect(() => {
    let interval = null;
    const tick = () => { checkServerStatus(); };
    tick();
    const delay = serverStatus?.connection_state === 'ready' ? 60_000 : 15_000;
    interval = setInterval(tick, delay);
    return () => { if (interval) clearInterval(interval); };
  }, [checkServerStatus, serverStatus?.connection_state]);

  // Close popover on outside click
  useEffect(() => {
    function onClick(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [open]);

  const state = serverStatus?.connection_state || 'unknown';
  const meta = STATE_LABELS[state] || STATE_LABELS.unknown;
  const Icon = meta.icon;

  const toneClasses = {
    ok:    'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800',
    warn:  'bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800',
    error: 'bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300 border-red-200 dark:border-red-800',
  };
  const dotClasses = {
    ok:    'bg-emerald-500',
    warn:  'bg-amber-500',
    error: 'bg-red-500',
  };

  const counts = serverStatus?.database?.counts || {};
  const uptimeSeconds = serverStatus?.uptime_seconds;

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full border transition-colors ${toneClasses[meta.tone]}`}
        title="Server connection status"
      >
        <span className={`w-1.5 h-1.5 rounded-full ${dotClasses[meta.tone]} ${state !== 'ready' && state !== 'unknown' ? 'animate-pulse' : ''}`} />
        <span className="hidden sm:inline">{meta.label}</span>
        {state !== 'ready' && state !== 'unknown' ? (
          <Loader2 size={12} className="animate-spin" />
        ) : (
          <Activity size={12} />
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-72 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl shadow-lg z-50 p-3 text-left animate-fadeIn">
          <div className="flex items-start gap-2">
            <Icon size={16} className={`mt-0.5 shrink-0 ${
              meta.tone === 'ok' ? 'text-emerald-500'
              : meta.tone === 'error' ? 'text-red-500'
              : 'text-amber-500'
            }`} />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-gray-800 dark:text-gray-100">
                {meta.label}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 leading-relaxed">
                {serverStatus?.message || 'Checking server status...'}
              </p>

              {serverStatus?.database && (
                <div className="mt-2 text-xs text-gray-500 dark:text-gray-400 space-y-0.5">
                  <p>
                    Database:{' '}
                    <span className={serverStatus.database.ready ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'}>
                      {serverStatus.database.ready ? 'Connected' : 'Not reachable'}
                    </span>
                  </p>
                  {serverStatus.database.ready && (
                    <p>
                      {counts.games || 0} games, {counts.users || 0} users, {counts.reviews || 0} reviews
                    </p>
                  )}
                  {serverStatus.database.error && !serverStatus.database.ready && (
                    <p className="text-[10px] text-gray-400 dark:text-gray-500 mt-1 break-words">
                      {serverStatus.database.error}
                    </p>
                  )}
                </div>
              )}

              {typeof uptimeSeconds === 'number' && (
                <p className="mt-2 text-[10px] text-gray-400 dark:text-gray-500">
                  Server uptime: {Math.floor(uptimeSeconds / 60)} min
                </p>
              )}

              {serverStatus?.free_tier_notes && (
                <div className="mt-2 text-[11px] text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-2 leading-relaxed">
                  <div className="flex items-start gap-1.5">
                    <Info size={12} className="mt-0.5 shrink-0 text-gray-400" />
                    <span>{serverStatus.free_tier_notes}</span>
                  </div>
                </div>
              )}

              <button
                type="button"
                onClick={() => checkServerStatus()}
                disabled={isCheckingStatus}
                className="mt-3 w-full text-xs font-medium px-2 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 dark:disabled:bg-blue-800 text-white transition-colors disabled:cursor-not-allowed"
              >
                {isCheckingStatus ? 'Refreshing...' : 'Refresh status'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
