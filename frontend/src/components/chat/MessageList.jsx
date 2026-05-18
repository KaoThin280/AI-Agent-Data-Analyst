import React, { useRef, useEffect, useState, useCallback } from 'react';
import {
  Code, FileText, Loader2, Bot, User, ExternalLink,
  Image, AlertTriangle, RefreshCw,
  BugPlay, ChevronDown, ChevronUp
} from 'lucide-react';
import useAppStore from '../../store/useAppStore';
import { fetchFileContent, getTableData, fetchFileBlob } from '../../services/api';
import MarkdownRenderer from '../Renderers/MarkdownRenderer';
import DataTableViewer from '../Renderers/DataTableViewer';
import PlotlyHtmlRenderer from '../Renderers/PlotlyHtmlRenderer';
import VisualizationViewer from '../Charts/VisualizationViewer';

export default function MessageList({ onRetry, darkMode }) {
  const { messages: chatHistory, isLoading } = useAppStore();
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, isLoading]);

  if (chatHistory.length === 0 && !isLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-gray-400 px-4">
        <Bot size={56} className="mb-4 opacity-30" />
        <p className="text-lg font-medium text-gray-500">Start Analyzing Data</p>
        <p className="text-sm text-gray-400 mt-1 text-center max-w-md">
          Upload a CSV or Excel file and ask a question in natural language.
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 scroll-smooth">
      {chatHistory.map((msg, idx) => (
        <div
          key={idx}
          className={`flex gap-3 animate-fadeIn ${
            msg.role === 'user' ? 'justify-end' : 'justify-start'
          }`}
        >
          {msg.role === 'ai' && (
            <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/50 flex items-center justify-center shrink-0 mt-1">
              <Bot size={16} className="text-blue-600 dark:text-blue-400" />
            </div>
          )}

          <div
            className={`max-w-[85%] space-y-2 transition-all duration-300 ${
              msg.role === 'user'
                ? 'bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-3'
                : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm'
            }`}
          >
            {msg.role === 'user' ? (
              <div className="text-sm leading-relaxed whitespace-pre-wrap break-words">
                {msg.content}
              </div>
            ) : (
              <div className="transition-colors text-gray-900 dark:text-gray-100">
                <MarkdownRenderer content={msg.content} />
              </div>
            )}

            {/* ── Generated Code Section ── */}
            {msg.code && <CodeSection code={msg.code} />}

            {/* ── Execution Logs Section ── */}
            {msg.logs && <LogsSection logs={msg.logs} />}

            {/* ── File Attachments ── */}
            {msg.files && msg.files.length > 0 && <FileAttachments files={msg.files} />}

            {/* ── Retry Badge ── */}
            {msg.retries !== undefined && msg.retries > 0 && (
              <div className="text-xs text-amber-500 dark:text-amber-400 mt-1 flex items-center gap-1">
                <AlertTriangle size={12} />
                <span>Retried {msg.retries} time{msg.retries !== 1 ? 's' : ''}</span>
              </div>
            )}

            {/* ── Error State with Retry Button ── */}
            {msg.error && (
              <ErrorState
                message={msg.error}
                onRetry={() => onRetry && onRetry(msg)}
                darkMode={darkMode}
              />
            )}
          </div>

          {msg.role === 'user' && (
            <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center shrink-0 mt-1">
              <User size={16} className="text-white" />
            </div>
          )}
        </div>
      ))}

      {isLoading && <LoadingIndicator darkMode={darkMode} />}
      <div ref={endRef} />
    </div>
  );
}

/* ── Code Section (collapsible with copy button) ─────────────────── */
function CodeSection({ code }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="mt-2 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden transition-all duration-300">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center gap-2 px-3 py-2 text-xs font-mono bg-gray-50 dark:bg-gray-900 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
      >
        <Code size={14} />
        <span className="font-medium">Generated Code</span>
        <span className="ml-auto text-gray-400 dark:text-gray-500">
          {isOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </span>
      </button>
      {isOpen && (
        <div className="relative group">
          <button
            onClick={() => navigator.clipboard.writeText(code)}
            className="absolute right-2 top-2 text-xs text-gray-400 hover:text-white bg-gray-700 hover:bg-gray-600 px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity z-10"
          >
            Copy
          </button>
          <pre className="p-3 bg-gray-900 text-green-300 text-xs leading-relaxed overflow-x-auto max-h-48 overflow-y-auto m-0">
            <code>{code}</code>
          </pre>
        </div>
      )}
    </div>
  );
}

/* ── Logs Section (collapsible) ──────────────────────────────────── */
function LogsSection({ logs }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="mt-2 border border-amber-200 dark:border-amber-800 rounded-lg overflow-hidden transition-all duration-300">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center gap-2 px-3 py-2 text-xs font-mono bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 hover:bg-amber-100 dark:hover:bg-amber-900/50 transition-colors"
      >
        <BugPlay size={14} />
        <span className="font-medium">Execution Logs</span>
        <span className="ml-auto text-amber-500 dark:text-amber-400">
          {isOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </span>
      </button>
      {isOpen && (
        <pre className="p-3 bg-gray-900 text-gray-300 text-xs leading-relaxed overflow-x-auto max-h-40 overflow-y-auto whitespace-pre-wrap font-mono m-0">
          {logs}
        </pre>
      )}
    </div>
  );
}

/* ── Error State ─────────────────────────────────────────────────── */
function ErrorState({ message, onRetry }) {
  return (
    <div className="mt-3 px-3 py-2 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg flex flex-col gap-2 animate-slideDown">
      <div className="flex items-start gap-2 text-xs text-red-700 dark:text-red-300">
        <AlertTriangle size={14} className="mt-0.5 shrink-0" />
        <span className="leading-relaxed">{message}</span>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="self-start flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-red-100 dark:bg-red-800 text-red-700 dark:text-red-300 rounded-lg hover:bg-red-200 dark:hover:bg-red-700 transition-colors"
        >
          <RefreshCw size={12} />
          <span>Retry</span>
        </button>
      )}
    </div>
  );
}

/* ── File Attachments ────────────────────────────────────────────── */
function FileAttachments({ files }) {
  const [expandedHtml, setExpandedHtml] = useState(null);
  const [htmlContents, setHtmlContents] = useState({});
  const [expandedCsv, setExpandedCsv] = useState(null);
  const [csvData, setCsvData] = useState({});
  const [imageUrls, setImageUrls] = useState({});

  const htmlFiles = files.filter(f => f.toLowerCase().endsWith('.html'));
  const csvFiles = files.filter(f => f.toLowerCase().endsWith('.csv'));
  const pngFiles = files.filter(f => /\.(png|jpg|jpeg|gif|svg|webp)$/i.test(f));
  const otherFiles = files.filter(f => {
    const lower = f.toLowerCase();
    return !lower.endsWith('.html') && !lower.endsWith('.csv') && !/\.(png|jpg|jpeg|gif|svg|webp)$/i.test(lower);
  });

  const handleToggleHtml = useCallback(async (fileName) => {
    if (expandedHtml === fileName) {
      setExpandedHtml(null);
      return;
    }
    setExpandedHtml(fileName);
    if (!htmlContents[fileName]) {
      try {
        const content = await fetchFileContent(fileName);
        setHtmlContents(prev => ({ ...prev, [fileName]: content }));
      } catch (err) {
        console.error('Failed to fetch HTML:', err);
      }
    }
  }, [expandedHtml, htmlContents]);

  const handleToggleCsv = useCallback(async (fileName) => {
    if (expandedCsv === fileName) {
      setExpandedCsv(null);
      return;
    }
    setExpandedCsv(fileName);
    if (!csvData[fileName]) {
      try {
        const data = await getTableData(fileName);
        setCsvData(prev => ({ ...prev, [fileName]: data }));
      } catch (err) {
        console.error('Failed to fetch CSV data:', err);
      }
    }
  }, [expandedCsv, csvData]);

  // Fetch image blobs for PNG files
  useEffect(() => {
    pngFiles.forEach(async (f) => {
      if (!imageUrls[f]) {
        try {
          const url = await fetchFileBlob(f);
          setImageUrls(prev => ({ ...prev, [f]: url }));
        } catch (err) {
          console.error('Failed to load image:', f, err);
        }
      }
    });
  }, [pngFiles, imageUrls]);

  return (
    <div className="mt-2 space-y-2">
      {/* CSV Files */}
      {csvFiles.map((file, fi) => (
        <div key={`csv-${fi}`}>
          <button
            onClick={() => handleToggleCsv(file)}
            className="inline-flex items-center gap-1 text-xs bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-800 px-2.5 py-1 rounded-full hover:bg-green-100 dark:hover:bg-green-900/50 transition-colors"
          >
            <FileText size={12} /> {file}
            <span className="text-green-400 dark:text-green-500">{expandedCsv === file ? '▲' : '▼'}</span>
          </button>
          {expandedCsv === file && csvData[file] && (
            <div className="mt-1 ml-1 animate-fadeIn">
              <DataTableViewer
                columns={csvData[file].columns}
                data={csvData[file].data}
                tableName={csvData[file].table_name || file}
              />
            </div>
          )}
        </div>
      ))}

      {/* Visualization Viewer for HTML + PNG charts */}
      {htmlFiles.length + pngFiles.length > 0 && (
        <VisualizationViewer
          files={[...htmlFiles, ...pngFiles]}
          captions={null}
          title="Generated Charts"
        />
      )}

      {/* Other Files */}
      {otherFiles.map((file, fi) => (
        <div key={`other-${fi}`} className="inline-flex items-center gap-1 text-xs bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800 px-2.5 py-1 rounded-full mr-1">
          <FileText size={12} /> {file}
        </div>
      ))}
    </div>
  );
}

/* ── Loading Indicator with Typing Animation ────────────────────── */
function LoadingIndicator({ darkMode }) {
  return (
    <div className="flex gap-3 justify-start animate-fadeIn">
      <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/50 flex items-center justify-center shrink-0">
        <Bot size={16} className="text-blue-600 dark:text-blue-400" />
      </div>
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
        <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
          <Loader2 size={16} className="animate-spin" />
          <span>AI is analyzing and writing code...</span>
        </div>
        <div className="mt-3 flex gap-1.5">
          <span className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
          <span className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
          <span className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
        </div>
      </div>
    </div>
  );
}
