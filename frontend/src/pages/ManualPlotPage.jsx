import React, { useState, useEffect } from 'react';
import { RefreshCw, Database, ChevronRight, Loader2, AlertCircle } from 'lucide-react';
import { getTableData, getFilesList } from '../services/api';
import useAppStore from '../store/useAppStore';
import ManualChartBuilder from '../components/Charts/ManualChartBuilder';

export default function ManualPlotPage() {
  const { files: uploadedFiles, currentDataContext } = useAppStore();
  const [selectedTable, setSelectedTable] = useState('');
  const [tableData, setTableData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sourceFiles, setSourceFiles] = useState([]);

  // Gather available tables from uploaded files + session
  useEffect(() => {
    const names = uploadedFiles.map(f => f.name);
    setSourceFiles(names);
    if (names.length > 0 && !selectedTable) {
      setSelectedTable(names[0]);
    }
  }, [uploadedFiles]);

  // Fetch data when table changes
  useEffect(() => {
    if (!selectedTable) return;
    fetchTableData(selectedTable);
  }, [selectedTable]);

  const fetchTableData = async (tableName) => {
    setIsLoading(true);
    setError(null);
    setTableData(null);
    try {
      const response = await getTableData(tableName);
      setTableData(response);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-bold text-gray-800">V\u1EBD bi\u1EC3u \u0111\u1ED3 th\u1EE7 c\u00F4ng</h2>
          <p className="text-sm text-gray-500 mt-0.5">Ch\u1ECDn c\u1ED9t v\u00E0 lo\u1EA1i bi\u1EC3u \u0111\u1ED3 \u0111\u1EC3 t\u1EF1 v\u1EBD</p>
        </div>
        <button
          onClick={() => { if (selectedTable) fetchTableData(selectedTable); }}
          disabled={isLoading || !selectedTable}
          className="flex items-center gap-1.5 text-sm px-3 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-40 transition-colors"
        >
          <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
          L\u00E0m m\u1EDBi
        </button>
      </div>

      <div className="flex-1 flex overflow-hidden gap-4">
        {/* Sidebar: table list */}
        <div className="w-56 shrink-0 bg-white border border-gray-200 rounded-xl overflow-y-auto">
          <div className="p-3 border-b bg-gray-50">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">B\u1EA3ng d\u1EEF li\u1EC7u</h3>
          </div>
          <ul className="p-2 space-y-0.5">
            {sourceFiles.length === 0 ? (
              <li className="text-xs text-gray-400 p-3 text-center italic">
                Ch\u01B0a c\u00F3 d\u1EEF li\u1EC7u.<br />Upload file \u1EDF tab Chat.
              </li>
            ) : (
              sourceFiles.map((name) => (
                <li key={name}>
                  <button
                    onClick={() => setSelectedTable(name)}
                    className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-left transition-colors ${
                      selectedTable === name
                        ? 'bg-blue-50 text-blue-700 font-medium'
                        : 'text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    <Database size={14} className="shrink-0" />
                    <span className="truncate">{name}</span>
                    {selectedTable === name && <ChevronRight size={14} className="ml-auto shrink-0" />}
                  </button>
                </li>
              ))
            )}
          </ul>
        </div>

        {/* Main: chart builder */}
        <div className="flex-1 overflow-y-auto">
          {!selectedTable ? (
            <div className="h-full flex flex-col items-center justify-center text-gray-400">
              <Database size={48} className="mb-3 opacity-30" />
              <p className="text-sm">Ch\u1ECDn m\u1ED9t b\u1EA3ng d\u1EEF li\u1EC7u \u0111\u1EC3 b\u1EAFt \u0111\u1EA7u</p>
            </div>
          ) : isLoading ? (
            <div className="h-full flex flex-col items-center justify-center">
              <Loader2 size={28} className="animate-spin text-blue-500 mb-3" />
              <p className="text-sm text-gray-500">\u0110ang t\u1EA3i d\u1EEF li\u1EC7u...</p>
            </div>
          ) : error ? (
            <div className="flex items-start gap-2 p-4 bg-red-50 border border-red-200 rounded-xl">
              <AlertCircle size={18} className="text-red-500 mt-0.5 shrink-0" />
              <div>
                <p className="text-sm font-medium text-red-700">L\u1ED7i t\u1EA3i d\u1EEF li\u1EC7u</p>
                <p className="text-xs text-red-600 mt-0.5">{error}</p>
              </div>
            </div>
          ) : tableData ? (
            <ManualChartBuilder
              data={tableData.data}
              columns={tableData.columns}
              tableName={tableData.table_name || selectedTable}
            />
          ) : null}
        </div>
      </div>
    </div>
  );
}