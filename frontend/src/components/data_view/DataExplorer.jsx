import React, { useState, useMemo } from 'react';

// ── Helper: infer column type from values ──────────────────────────
function inferColumnType(values) {
  const sample = values.filter(v => v != null && v !== '').slice(0, 50);
  if (sample.length === 0) return 'text';

  const isNum = sample.every(v => /^-?\d+(\.\d+)?$/.test(String(v).trim()));
  if (isNum) return 'number';

  const isDate = sample.every(v => !isNaN(Date.parse(String(v))));
  if (isDate) return 'date';

  const isBool = sample.every(v => ['true', 'false', 'yes', 'no', '1', '0'].includes(String(v).toLowerCase()));
  if (isBool) return 'boolean';

  return 'text';
}

// ── Helper: compute quick stats for a column ────────────────────────
function computeColumnStats(rows, colName) {
  const vals = rows.map(r => r[colName]);
  const nonNull = vals.filter(v => v != null && v !== '');
  const nulls = vals.length - nonNull.length;
  const unique = new Set(nonNull.map(v => String(v))).size;
  const type = inferColumnType(vals);
  return { total: vals.length, nulls, nonNull, unique, type };
}

// ── Type badge colors ──────────────────────────────────────────────
const TYPE_COLORS = {
  number:   'bg-blue-100 text-blue-800',
  date:     'bg-green-100 text-green-800',
  boolean:  'bg-purple-100 text-purple-800',
  text:     'bg-gray-100 text-gray-800',
};

const TYPE_COLORS_DARK = {
  number:   'dark:bg-blue-900/40 dark:text-blue-300',
  date:     'dark:bg-green-900/40 dark:text-green-300',
  boolean:  'dark:bg-purple-900/40 dark:text-purple-300',
  text:     'dark:bg-gray-700/40 dark:text-gray-300',
};

// ── Main DataExplorer component ───────────────────────────────────
export default function DataExplorer({ fileName, rows, columns }) {
  // ── State ──────────────────────────────────────────────────────
  const [sortKey, setSortKey] = useState(null);
  const [sortDir, setSortDir] = useState('asc');
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [selectedCols, setSelectedCols] = useState(() =>
    columns.reduce((acc, c) => { acc[c] = true; return acc; }, {})
  );
  const pageSize = 20;

  // ── Column stats ──────────────────────────────────────────────────
  const colStats = useMemo(() => {
    return columns.reduce((acc, col) => {
      acc[col] = computeColumnStats(rows, col);
      return acc;
    }, {});
  }, [rows, columns]);

  // ── Summary stats ─────────────────────────────────────────────
  const totalMissing = useMemo(() => {
    return Object.values(colStats).reduce((sum, s) => sum + s.nulls, 0);
  }, [colStats]);

  const typeSummary = useMemo(() => {
    const counts = {};
    Object.values(colStats).forEach(s => {
      counts[s.type] = (counts[s.type] || 0) + 1;
    });
    return Object.entries(counts).map(([t, c]) => `${t}: ${c}`).join(', ');
  }, [colStats]);

  // ── Filter, Sort, Paginate ───────────────────────────────────────
  const processed = useMemo(() => {
    let data = [...rows];
    // search filter
    if (search.trim()) {
      const q = search.toLowerCase();
      data = data.filter(row =>
        Object.entries(row).some(([k, v]) => {
          if (!selectedCols[k]) return false;
          return String(v ?? '').toLowerCase().includes(q);
        })
      );
    }
    // sort
    if (sortKey) {
      data.sort((a, b) => {
        const va = a[sortKey] ?? '';
        const vb = b[sortKey] ?? '';
        const cmp = typeof va === 'number' ? va - vb : String(va).localeCompare(String(vb));
        return sortDir === 'asc' ? cmp : -cmp;
      });
    }
    return data;
  }, [rows, search, sortKey, sortDir, selectedCols]);

  const totalPages = Math.ceil(processed.length / pageSize);
  const safePage = Math.min(page, totalPages || 1);
  const pageData = processed.slice((safePage - 1) * pageSize, safePage * pageSize);

  // ── Handlers ────────────────────────────────────────────────────
  const handleSort = (col) => {
    if (sortKey === col) {
      setSortDir(d => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(col);
      setSortDir('asc');
    }
  };

  const toggleCol = (col) => {
    setSelectedCols(prev => ({
      ...prev,
      [col]: !prev[col],
    }));
  };

  const selectAll = () => {
    setSelectedCols(columns.reduce((acc, c) => { acc[c] = true; return acc; }, {}));
  };

  const deselectAll = () => {
    setSelectedCols(columns.reduce((acc, c) => { acc[c] = false; return acc; }, {}));
  };

  // ── Render ────────────────────────────────────────────────────────
  return (
    <div className="w-full space-y-4">
      {/* ── Summary Card ─────────────────────────────────────────── */}
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-gray-800">
        <h3 className="mb-3 text-lg font-semibold text-gray-800 dark:text-gray-100">
          📊 Dataset Summary
        </h3>
        <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-5">
          <div>
            <span className="text-gray-500 dark:text-gray-400">File</span>
            <p className="font-medium text-gray-800 dark:text-gray-100 truncate">{fileName}</p>
          </div>
          <div>
            <span className="text-gray-500 dark:text-gray-400">Rows</span>
            <p className="font-medium text-gray-800 dark:text-gray-100">{rows.length.toLocaleString()}</p>
          </div>
          <div>
            <span className="text-gray-500 dark:text-gray-400">Columns</span>
            <p className="font-medium text-gray-800 dark:text-gray-100">{columns.length}</p>
          </div>
          <div>
            <span className="text-gray-500 dark:text-gray-400">Missing</span>
            <p className="font-medium text-yellow-600 dark:text-yellow-400">{totalMissing.toLocaleString()}</p>
          </div>
          <div className="col-span-2 sm:col-span-1">
            <span className="text-gray-500 dark:text-gray-400">Types</span>
            <p className="font-medium text-gray-800 dark:text-gray-100 text-xs leading-tight">{typeSummary}</p>
          </div>
        </div>
      </div>

      {/* ── Controls ──────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-2">
        {/* Search */}
        <input
          type="text"
          placeholder="🔍 Search within selected columns..."
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1); }}
          className="flex-1 min-w-[200px] rounded border border-gray-300 px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
        />

        {/* Column selection toggles */}
        <div className="flex items-center gap-1">
          <button onClick={selectAll} className="rounded bg-gray-100 px-2 py-1 text-xs hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600">All</button>
          <button onClick={deselectAll} className="rounded bg-gray-100 px-2 py-1 text-xs hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600">None</button>
        </div>

        {/* Pagination info */}
        <span className="text-xs text-gray-500 dark:text-gray-400 ml-auto">
          {processed.length.toLocaleString()} row{processed.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* ── Column type badges + quick stats ──────────────────────── */}
      <div className="flex flex-wrap gap-1.5">
        {columns.map(col => (
          <label key={col} className="inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs cursor-pointer select-none transition-colors
            dark:border-gray-600
            ${selectedCols[col] ? 'border-blue-400 bg-blue-50 dark:border-blue-500 dark:bg-blue-900/30' : 'border-gray-200 bg-white dark:bg-gray-700'}"
          >
            <input
              type="checkbox"
              checked={!!selectedCols[col]}
              onChange={() => toggleCol(col)}
              className="sr-only"
            />
            <span className="font-medium text-gray-700 dark:text-gray-200">{col}</span>
            <span className={`rounded px-1 py-0.5 text-[10px] font-semibold ${TYPE_COLORS[colStats[col]?.type] || TYPE_COLORS.text} ${TYPE_COLORS_DARK[colStats[col]?.type] || TYPE_COLORS_DARK.text}`}>
              {colStats[col]?.type}
            </span>
            {selectedCols[col] && (
              <span className="text-gray-400 dark:text-gray-500">
                {colStats[col]?.nonNull}/{colStats[col]?.total} · {colStats[col]?.nulls} null · {colStats[col]?.unique} unique
              </span>
            )}
          </label>
        ))}
      </div>

      {/* ── Table ──────────────────────────────────────────────────── */}
      <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700 text-sm">
          <thead className="bg-gray-50 dark:bg-gray-800">
            <tr>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider w-10">#</th>
              {columns.filter(c => selectedCols[c]).map(col => (
                <th
                  key={col}
                  onClick={() => handleSort(col)}
                  className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 whitespace-nowrap"
                >
                  <span className="inline-flex items-center gap-1">
                    {col}
                    {sortKey === col && (
                      <span className="text-blue-500">{sortDir === 'asc' ? '▲' : '▼'}</span>
                    )}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700 bg-white dark:bg-gray-900">
            {pageData.length === 0 ? (
              <tr>
                <td colSpan={columns.filter(c => selectedCols[c]).length + 1} className="px-3 py-8 text-center text-gray-400 dark:text-gray-500">
                  No data found.
                </td>
              </tr>
            ) : (
              pageData.map((row, i) => (
                <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                  <td className="px-3 py-1.5 text-gray-400 dark:text-gray-500 text-xs">
                    {(safePage - 1) * pageSize + i + 1}
                  </td>
                  {columns.filter(c => selectedCols[c]).map(col => (
                    <td key={col} className="px-3 py-1.5 text-gray-700 dark:text-gray-200 whitespace-nowrap max-w-[200px] truncate">
                      {row[col] != null ? String(row[col]) : <span className="text-red-300 dark:text-red-500">—</span>}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* ── Pagination ───────────────────────────────────────────── */}
      <div className="flex items-center justify-between text-sm">
        <span className="text-gray-500 dark:text-gray-400">
          Page {safePage} of {totalPages || 1}
        </span>
        <div className="flex items-center gap-1">
          <button
            disabled={safePage <= 1}
            onClick={() => setPage(1)}
            className="rounded px-2 py-1 text-xs disabled:opacity-40 hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            ««
          </button>
          <button
            disabled={safePage <= 1}
            onClick={() => setPage(p => Math.max(1, p - 1))}
            className="rounded px-2 py-1 text-xs disabled:opacity-40 hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            ‹
          </button>
          <input
            type="number"
            min={1}
            max={totalPages || 1}
            value={safePage}
            onChange={e => { const v = parseInt(e.target.value, 10); if (v >= 1 && v <= totalPages) setPage(v); }}
            className="w-12 rounded border border-gray-300 px-2 py-1 text-center text-xs dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
          />
          <button
            disabled={safePage >= totalPages}
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            className="rounded px-2 py-1 text-xs disabled:opacity-40 hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            ›
          </button>
          <button
            disabled={safePage >= totalPages}
            onClick={() => setPage(totalPages)}
            className="rounded px-2 py-1 text-xs disabled:opacity-40 hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            »»
          </button>
        </div>
      </div>
    </div>
  );
}