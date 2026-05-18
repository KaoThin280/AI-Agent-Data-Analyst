import React, { useState, useMemo } from 'react';
import { ChevronLeft, ChevronRight, Download } from 'lucide-react';

const ROWS_PER_PAGE_OPTIONS = [10, 25, 50, 100];

export default function DataTableViewer({ columns, data, tableName }) {
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(ROWS_PER_PAGE_OPTIONS[0]);
  const [sortKey, setSortKey] = useState(null);
  const [sortDir, setSortDir] = useState('asc');

  const colNames = columns
    ? Object.keys(columns)
    : (data && data.length > 0 ? Object.keys(data[0]) : []);

  const sortedData = useMemo(() => {
    if (!data || data.length === 0) return [];
    let rows = [...data];
    if (sortKey) {
      rows.sort((a, b) => {
        const va = a[sortKey];
        const vb = b[sortKey];
        if (va == null) return 1;
        if (vb == null) return -1;
        if (typeof va === 'number' && typeof vb === 'number') {
          return sortDir === 'asc' ? va - vb : vb - va;
        }
        return sortDir === 'asc'
          ? String(va).localeCompare(String(vb))
          : String(vb).localeCompare(String(va));
      });
    }
    return rows;
  }, [data, sortKey, sortDir]);

  const totalPages = Math.max(1, Math.ceil(sortedData.length / rowsPerPage));
  const safePage = Math.min(currentPage, totalPages);
  const pageData = sortedData.slice((safePage - 1) * rowsPerPage, safePage * rowsPerPage);

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  const handleExportCSV = () => {
    if (!data || data.length === 0) return;
    const headers = colNames.join(',');
    const rows = data.map(row =>
      colNames.map(col => {
        const val = row[col];
        if (val == null) return '';
        const str = String(val);
        return str.includes(',') || str.includes('"') || str.includes('\n')
          ? `"${str.replace(/"/g, '""')}"`
          : str;
      }).join(',')
    );
    const csv = [headers, ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${tableName || 'data'}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!data || data.length === 0) {
    return (
      <div className="text-center text-gray-400 py-8 text-sm">
        Kh\u00F4ng c\u00F3 d\u1EEF li\u1EC7u \u0111\u1EC3 hi\u1EC3n th\u1ECB.
      </div>
    );
  }

  return (
    <div className="my-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-gray-500">
          {sortedData.length} d\u00F2ng
          {sortKey && ` \u2022 S\u1EAFp x\u1EBFp theo "${sortKey}"`}
        </span>
        <button
          onClick={handleExportCSV}
          className="flex items-center gap-1 text-xs text-gray-500 hover:text-blue-600 transition-colors"
        >
          <Download size={14} />
          CSV
        </button>
      </div>

      <div className="overflow-x-auto border border-gray-200 rounded-lg">
        <table className="min-w-full divide-y divide-gray-200">
          <thead>
            <tr className="bg-gray-50">
              {colNames.map((col) => (
                <th
                  key={col}
                  onClick={() => handleSort(col)}
                  className={`px-3 py-2.5 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider cursor-pointer select-none hover:bg-gray-100 transition-colors ${
                    sortKey === col ? 'text-blue-600' : ''
                  }`}
                >
                  <div className="flex items-center gap-1">
                    {columns?.[col]?.business_meaning
                      ? `${col} (${columns[col].business_meaning})`
                      : col}
                    {sortKey === col && (
                      <span className="text-blue-500">{sortDir === 'asc' ? '\u25B2' : '\u25BC'}</span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-100">
            {pageData.map((row, ri) => (
              <tr key={ri} className="hover:bg-gray-50 transition-colors">
                {colNames.map((col) => {
                  const val = row[col];
                  const display =
                    val == null ? (
                      <span className="text-gray-300 italic">\u2014</span>
                    ) : typeof val === 'number' ? (
                      Number.isInteger(val) ? val.toLocaleString() : val.toFixed(4)
                    ) : (
                      String(val)
                    );
                  return (
                    <td
                      key={col}
                      className={`px-3 py-2 text-sm text-gray-700 whitespace-nowrap ${
                        typeof val === 'number' ? 'text-right font-mono' : ''
                      }`}
                    >
                      {display}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between mt-3 text-sm">
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">Hi\u1EC3n th\u1ECB</span>
          <select
            value={rowsPerPage}
            onChange={(e) => { setRowsPerPage(Number(e.target.value)); setCurrentPage(1); }}
            className="text-xs border border-gray-300 rounded px-2 py-1 bg-white"
          >
            {ROWS_PER_PAGE_OPTIONS.map(n => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
          <span className="text-xs text-gray-500">/ trang</span>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">
            Trang {safePage}/{totalPages}
          </span>
          <button
            onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
            disabled={safePage <= 1}
            className="p-1 rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <ChevronLeft size={16} />
          </button>
          <button
            onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
            disabled={safePage >= totalPages}
            className="p-1 rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}