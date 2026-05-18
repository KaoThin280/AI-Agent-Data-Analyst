import DataExplorerModal from '../data_view/DataExplorerModal';  // thêm import mới
import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Upload, AlertCircle, Loader2, CheckCircle, FileText, Eye, EyeOff, ChevronDown, ChevronUp, Trash2, Table2, X } from 'lucide-react';
import { uploadFile, fetchFilePreview } from '../../services/api';
import useAppStore from '../../store/useAppStore';

function formatSize(bytes) {
  if (!bytes || bytes === 0) return '0';
  const units = ['B', 'KB', 'MB', 'GB'];
  let i = 0;
  let size = bytes;
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024;
    i++;
  }
  return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

function FilePreviewTable({ columns, rows }) {
  const colKeys = Object.keys(columns);
  if (!colKeys.length || !rows.length) return null;

  return (
    <div className="overflow-x-auto max-h-48 overflow-y-auto rounded-lg border border-gray-200">
      <table className="min-w-full text-xs divide-y divide-gray-200">
        <thead className="bg-gray-50 sticky top-0">
          <tr>
            {colKeys.slice(0, 8).map((col) => (
              <th key={col} className="px-3 py-2 text-left font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap">
                {col}
                <span className="ml-1 text-gray-400 font-normal">({columns[col]})</span>
              </th>
            ))}
            {colKeys.length > 8 && (
              <th className="px-3 py-2 text-left font-medium text-gray-400">+{colKeys.length - 8} more</th>
            )}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-100">
          {rows.map((row, ri) => (
            <tr key={ri} className="hover:bg-gray-50">
              {colKeys.slice(0, 8).map((col) => (
                <td key={col} className="px-3 py-1.5 text-gray-600 truncate max-w-[120px]">
                  {row[col] !== null && row[col] !== undefined ? String(row[col]) : '—'}
                </td>
              ))}
              {colKeys.length > 8 && <td className="px-3 py-1.5 text-gray-400">…</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function FileUploader() {
  const {
    addUploadedFile,
    addMessage,            // ← THÊM: đẩy AI Overview vào chat
    setDataContext,
    setLoading,
    ensureSession,
    files,
    selectedFiles,
    toggleFileSelection,
    removeUploadedFile,
    selectAllFiles,
    deselectAllFiles,
    filePreviews,
    setFilePreview,
  } = useAppStore();

  const [isDragOver, setIsDragOver] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [exploringFile, setExploringFile] = useState(null);
  const [error, setError] = useState(null);
  const [previewOpen, setPreviewOpen] = useState({});
  const [uploadingFile, setUploadingFile] = useState(null);
  const fileInputRef = useRef(null);
  const dropZoneRef = useRef(null);

  const processFile = useCallback(async (file) => {
    if (!file) return;

    setError(null);

    // File type validation — only .csv
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (ext !== '.csv') {
      setError(`Invalid format: ${ext}. Only .csv files are accepted.`);
      return;
    }
    

    // Size check (max 100MB)
    const maxSize = 100 * 1024 * 1024;
    if (file.size > maxSize) {
      setError(`File too large (${formatSize(file.size)}). Maximum is 100MB.`);
      return;
    }

    // Check duplicates
    if (files.some((f) => f.name === file.name)) {
      setError(`File "${file.name}" has already been uploaded.`);
      return;
    }

    setIsUploading(true);
    setUploadingFile(file.name);
    setLoading(true);
    ensureSession();

    try {
      const data = await uploadFile(file);

      const fileInfo = {
        name: data.file_name || file.name,
        size: file.size,
        rows: data.num_rows || 0,
        cols: data.num_columns || 0,
        overview: data.ai_analysis || '',
        dataContext: data.data_context || null,
      };

      addUploadedFile(fileInfo);
      if (data.data_context) setDataContext(data.data_context);

      // Add AI overview as a chat message so it appears in the chat
      if (data.ai_analysis) {
        addMessage({
          id: Date.now() + 1,
          role: 'ai',
          content: data.ai_analysis,
          files: [fileInfo.name],
          logs: null,
          error: null,
        });
      }

      // Fetch preview (first 5 rows)
      try {
        const preview = await fetchFilePreview(fileInfo.name);
        if (preview) {
          setFilePreview(fileInfo.name, preview);
        }
      } catch {
        // Preview is non-critical
      }
    } catch (err) {
      setError(err.message || 'Upload failed');
    } finally {
      setIsUploading(false);
      setUploadingFile(null);
      setLoading(false);
    }
  }, [files, addUploadedFile, addMessage, setDataContext, setLoading, ensureSession, setFilePreview]);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      processFile(files[0]);
    }
  }, [processFile]);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleClick = () => {
    if (!isUploading) fileInputRef.current?.click();
  };

  const handleInputChange = (e) => {
    const file = e.target.files[0];
    processFile(file);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const togglePreview = (fileName) => {
    setPreviewOpen((prev) => ({ ...prev, [fileName]: !prev[fileName] }));
  };

  const handleRemove = (fileName) => {
    removeUploadedFile(fileName);
  };

  const allSelected = files.length > 0 && selectedFiles.length === files.length;

  return (
    <div className="space-y-4">
      {/* Drag & Drop Zone */}
      <div
        ref={dropZoneRef}
        onClick={handleClick}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`
          relative border-2 border-dashed rounded-xl p-8
          flex flex-col items-center justify-center cursor-pointer
          transition-all duration-200
          ${isDragOver
            ? 'border-blue-400 bg-blue-50 scale-[1.01]'
            : isUploading
              ? 'border-blue-300 bg-blue-50/50'
              : error
                ? 'border-red-300 bg-red-50/50'
                : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
          }
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept=".csv"
          onChange={handleInputChange}
          disabled={isUploading}
        />

        {isUploading ? (
          <>
            <div className="relative mb-3">
              <Loader2 size={40} className="text-blue-500 animate-spin" />
            </div>
            <div className="text-center">
              <p className="text-sm font-medium text-blue-600">Uploading {uploadingFile}...</p>
              <div className="mt-3 w-48 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                <div className="h-full bg-blue-500 rounded-full animate-pulse w-2/3" />
              </div>
              <p className="text-xs text-gray-400 mt-2">AI is processing your data</p>
            </div>
          </>
        ) : (
          <>
            <div className={`p-3 rounded-full mb-3 transition-colors ${isDragOver ? 'bg-blue-100' : 'bg-gray-100'}`}>
              <Upload size={28} className={isDragOver ? 'text-blue-500' : 'text-gray-400'} />
            </div>
            <div className="text-center">
              <p className="text-sm font-medium text-gray-600">
                {isDragOver ? 'Drop your file here' : 'Drag & drop your CSV file here'}
              </p>
              <p className="text-xs text-gray-400 mt-1.5">
                or <span className="text-blue-500 underline">browse files</span>
              </p>
              <p className="text-xs text-gray-400 mt-0.5">.csv only — max 100MB</p>
            </div>
          </>
        )}
      </div>

      {/* Error Message */}
      {error && (
        <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-sm">
          <AlertCircle size={16} className="text-red-500 mt-0.5 shrink-0" />
          <span className="text-red-700 flex-1">{error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-600">
            <X size={16} />
          </button>
        </div>
      )}

      {/* Uploaded Files List */}
      {files.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-700">
              Uploaded Files ({files.length})
            </h3>
            <div className="flex items-center gap-2">
              <button
                onClick={allSelected ? deselectAllFiles : selectAllFiles}
                className="text-xs text-blue-600 hover:text-blue-800 font-medium"
              >
                {allSelected ? 'Deselect All' : 'Select All'}
              </button>
            </div>
          </div>

          <div className="divide-y divide-gray-100">
            {files.map((file, idx) => {
              const isSelected = selectedFiles.includes(file.name);
              const preview = filePreviews[file.name];
              const isPreviewOpen = previewOpen[file.name];

              return (
                <div key={idx} className={`transition-colors ${isSelected ? 'bg-blue-50/40' : ''}`}>
                  {/* File Header Row */}
                  <div className="flex items-center gap-3 px-4 py-3">
                    {/* Checkbox */}
                    <button
                      onClick={() => toggleFileSelection(file.name)}
                      className={`
                        w-4 h-4 rounded border-2 flex items-center justify-center shrink-0 transition-colors
                        ${isSelected
                          ? 'bg-blue-600 border-blue-600 text-white'
                          : 'border-gray-300 hover:border-blue-400'
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
                    <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center shrink-0">
                      <FileText size={16} className="text-blue-600" />
                    </div>

                    {/* File Info */}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-800 truncate">{file.name}</p>
                      <div className="flex items-center gap-3 text-xs text-gray-400 mt-0.5">
                        <span>{formatSize(file.size)}</span>
                        {file.rows > 0 && <span>{file.rows.toLocaleString()} rows</span>}
                        {file.cols > 0 && <span>{file.cols} columns</span>}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => togglePreview(file.name)}
                        className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
                        title={isPreviewOpen ? 'Hide preview' : 'Show preview'}
                      >
                        {isPreviewOpen ? <EyeOff size={15} /> : <Eye size={15} />}
                      </button>
                      <button
                        onClick={() => setExploringFile(file.name)}
                        className="p-1.5 rounded-lg hover:bg-blue-50 text-gray-400 hover:text-blue-500 transition-colors"
                        title="Open full table explorer"
                      >
                        <Table2 size={15} />
                      </button>
                      <button
                        onClick={() => handleRemove(file.name)}
                        className="p-1.5 rounded-lg hover:bg-red-50 text-gray-400 hover:text-red-500 transition-colors"
                        title="Remove file"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </div>

                  {/* AI Overview */}
                  {file.overview && (
                    <div className="px-14 pb-1">
                      <div className="text-xs text-gray-500 bg-gray-50 rounded-lg p-2.5 leading-relaxed line-clamp-2">
                        {file.overview}
                      </div>
                    </div>
                  )}

                  {/* Preview Table (first 5 rows) */}
                  {isPreviewOpen && preview && (
                    <div className="px-14 pb-3">
                      <div className="flex items-center gap-1.5 mb-1.5">
                        <Table2 size={12} className="text-gray-400" />
                        <span className="text-xs text-gray-400">
                          Preview (first {preview.rows.length} of {preview.totalRows} rows)
                        </span>
                      </div>
                      <FilePreviewTable columns={preview.columns} rows={preview.rows} />
                    </div>
                  )}
                  
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Selection Status Bar */}
      {files.length > 0 && (
        <div className="flex items-center justify-between text-xs text-gray-500 px-1">
          <span>
            {selectedFiles.length === 0
              ? 'No files selected for analysis'
              : `${selectedFiles.length} of ${files.length} file(s) selected for analysis`
            }
          </span>
          {selectedFiles.length > 0 && (
            <span className="text-green-600 font-medium">
              <CheckCircle size={12} className="inline mr-1" />
              Ready
            </span>
          )}
        </div>
      )}
      {/* Data Explorer Modal */}
      {exploringFile && (
        <DataExplorerModal
          fileName={exploringFile}
          onClose={() => setExploringFile(null)}
        />
      )}
    </div>
   );
}