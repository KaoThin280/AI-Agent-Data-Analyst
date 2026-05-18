import React, { useState, useMemo } from 'react';
import { Table2, BarChart2, X } from 'lucide-react';
import useAppStore from '../../store/useAppStore';
import DataExplorer from '../data_view/DataExplorer';
import VisualizationViewer from '../charts/VisualizationViewer';

export default function RightPanel({ onClose, isCollapsed }) {
  const [activeTab, setActiveTab] = useState('data'); // 'data' | 'charts'
  const {
    files,
    selectedFiles,
    filePreviews,
    messages,
    setActiveView,
  } = useAppStore();

  // ── Data for Data Explorer ──────────────────────────────────────
  const activeFile = useMemo(() => {
    const name = selectedFiles.length > 0
      ? selectedFiles[0]
      : files[0]?.name;
    if (!name) return null;
    const preview = filePreviews[name];
    if (!preview) return null;
    return {
      fileName: name,
      rows: preview.rows || [],
      columns: Object.keys(preview.columns || {}),
    };
  }, [selectedFiles, files, filePreviews]);

  // ── Data for Chart Viewer ──────────────────────────────────────
  const chartFiles = useMemo(() => {
    const lastAiMsg = [...messages].reverse().find(m => m.role === 'ai' && m.files?.length);
    return lastAiMsg?.files?.filter(f =>
      f.toLowerCase().endsWith('.html') || /\.(png|jpg|jpeg|gif|svg|webp)$/i.test(f)
    ) || [];
  }, [messages]);

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    setActiveView(tab === 'data' ? 'data' : 'charts');
  };

  if (isCollapsed) return null;

  return (
    <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 flex flex-col transition-all duration-300 h-full">
      {/* Tab bar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 dark:border-gray-700 shrink-0">
        <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-800 p-0.5 rounded-lg">
          <button
            onClick={() => handleTabChange('data')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              activeTab === 'data'
                ? 'bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-400 shadow-sm'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            <Table2 size={14} />
            Data View
          </button>
          <button
            onClick={() => handleTabChange('charts')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              activeTab === 'charts'
                ? 'bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-400 shadow-sm'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            <BarChart2 size={14} />
            Charts
          </button>
        </div>

        {/* Close button */}
        <button
          onClick={onClose}
          className="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 dark:text-gray-500 transition-colors"
          title="Close right panel"
        >
          <X size={16} />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'data' ? (
          activeFile ? (
            <DataExplorer
              fileName={activeFile.fileName}
              rows={activeFile.rows}
              columns={activeFile.columns}
            />
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-gray-400 dark:text-gray-500 py-12">
              <Table2 size={40} className="mb-3 opacity-30" />
              <p className="text-sm font-medium">No data to display</p>
              <p className="text-xs mt-1">Select a file from the sidebar to explore its data.</p>
            </div>
          )
        ) : (
          chartFiles.length > 0 ? (
            <VisualizationViewer
              files={chartFiles}
              captions={null}
              title="Generated Charts"
            />
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-gray-400 dark:text-gray-500 py-12">
              <BarChart2 size={40} className="mb-3 opacity-30" />
              <p className="text-sm font-medium">No charts yet</p>
              <p className="text-xs mt-1">Ask the AI to analyze your data and generate charts.</p>
            </div>
          )
        )}
      </div>
    </div>
  );
}