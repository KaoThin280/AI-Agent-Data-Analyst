import React from 'react';
import { Upload, FileText, Database, ChevronDown, ChevronUp, X, Send, BarChart2 } from 'lucide-react';
import useAppStore from '../../store/useAppStore';
import FileUploader from '../Upload/FileUploader';

export default function Sidebar({ isOpen, setIsOpen, onAnalyze }) {
  const {
    files,
    selectedFiles,
    toggleFileSelection,
    selectAllFiles,
    deselectAllFiles,
    removeFile,
    uploadFile,
  } = useAppStore();

  const allSelected = files.length > 0 && selectedFiles.length === files.length;

  return (
    <div
      className={`
        ${isOpen ? 'w-80' : 'w-0'}
        transition-all duration-300 bg-white dark:bg-gray-900
        border-r border-gray-200 dark:border-gray-700
        overflow-hidden flex flex-col shrink-0
      `}
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between shrink-0">
        <h2 className="font-bold text-gray-700 dark:text-gray-200 text-lg flex items-center gap-2">
          <Database size={18} />
          Files
        </h2>
        <button
          onClick={() => setIsOpen(false)}
          className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 dark:text-gray-500 transition-colors"
        >
          <X size={18} />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Upload section */}
        <FileUploader />

        {/* Separator */}
        {files.length > 0 && (
          <hr className="border-gray-200 dark:border-gray-700" />
        )}

        {/* File list with checkboxes */}
        {files.length > 0 && (
          <div className="space-y-3">
            {/* Select / Deselect all */}
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">
                {files.length} file{files.length > 1 ? 's' : ''}
              </span>
              <button
                onClick={allSelected ? deselectAllFiles : selectAllFiles}
                className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 font-medium"
              >
                {allSelected ? 'Deselect All' : 'Select All'}
              </button>
            </div>

            {/* File items */}
            <ul className="space-y-1.5">
              {files.map((file, idx) => {
                const isSelected = selectedFiles.includes(file.name);

                return (
                  <li key={idx} className="flex items-center gap-2 py-1.5 px-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors group">
                    {/* Checkbox */}
                    <button
                      onClick={() => toggleFileSelection(file.name)}
                      className={`
                        w-4 h-4 rounded border-2 flex items-center justify-center shrink-0 transition-colors
                        ${isSelected
                          ? 'bg-blue-600 border-blue-600 text-white'
                          : 'border-gray-300 dark:border-gray-600 hover:border-blue-400'
                        }
                      `}
                    >
                      {isSelected && (
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                      )}
                    </button>

                    {/* Icon */}
                    <div className="w-7 h-7 rounded bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center shrink-0">
                      <FileText size={14} className="text-blue-600 dark:text-blue-400" />
                    </div>

                    {/* File info */}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-800 dark:text-gray-200 truncate">{file.name}</p>
                      <p className="text-xs text-gray-400 dark:text-gray-500">
                        {file.rows?.toLocaleString() || 0} rows · {file.columns || 0} cols
                      </p>
                    </div>

                    {/* Remove button */}
                    <button
                      onClick={() => removeFile(file.name)}
                      className="p-1 rounded hover:bg-red-50 dark:hover:bg-red-900/30 text-gray-300 dark:text-gray-600 hover:text-red-500 dark:hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
                    >
                      <X size={14} />
                    </button>
                  </li>
                );
              })}
            </ul>

            {/* Separator */}
            <hr className="border-gray-200 dark:border-gray-700" />

            {/* Selected files summary */}
            <div className="text-xs text-gray-500 dark:text-gray-400 space-y-1">
              <p>
                <span className="font-medium text-gray-700 dark:text-gray-300">{selectedFiles.length}</span> of{' '}
                <span className="font-medium text-gray-700 dark:text-gray-300">{files.length}</span> file(s) selected
              </p>
              {selectedFiles.length > 0 && (
                <ul className="pl-2 space-y-0.5 max-h-20 overflow-y-auto">
                  {selectedFiles.map((name, i) => (
                    <li key={i} className="flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-green-400 shrink-0" />
                      <span className="truncate">{name}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Analyze button — fixed at bottom */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-700 shrink-0">
        <button
          onClick={onAnalyze}
          disabled={selectedFiles.length === 0}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold
            bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 dark:disabled:bg-gray-700
            text-white disabled:text-gray-500 dark:disabled:text-gray-400
            transition-all duration-200 disabled:cursor-not-allowed"
        >
          <Send size={16} />
          {selectedFiles.length === 0
            ? 'Select files to analyze'
            : `Analyze ${selectedFiles.length} file${selectedFiles.length > 1 ? 's' : ''}`}
        </button>
      </div>
    </div>
  );
}