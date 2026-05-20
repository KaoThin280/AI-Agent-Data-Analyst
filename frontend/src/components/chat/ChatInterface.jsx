import React, { useState, useCallback } from 'react';
import { Send, Trash2, AlertCircle, RefreshCw } from 'lucide-react';
import useAppStore from '../../store/useAppStore';
import MessageList from './MessageList';

export default function ChatInterface({ darkMode }) {
  const {
    messages,
    files,
    selectedFiles,
    isLoading,
    error,
    sendMessage,
    clearChat,
    clearError,
  } = useAppStore();

  const [input, setInput] = useState('');

  const handleSend = useCallback(async (retryMessage = null) => {
    const query = retryMessage || input.trim();
    if ((!query && !retryMessage) || isLoading) return;

    setInput('');
    clearError();

    await sendMessage(query, retryMessage || null);
  }, [input, isLoading, sendMessage, clearError]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const canSend = () => {
    if (isLoading) return false;
    return input.trim().length > 0 && selectedFiles.length > 0;
  };

  return (
    <div className="h-full flex flex-col">
      {/* Chat Section */}
      <div className="flex-1 flex flex-col bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden transition-colors duration-300">
        <MessageList
          onRetry={(message) => handleSend(message._originalQuery || message.content)}
          darkMode={darkMode}
        />

        <div className="border-t border-gray-200 dark:border-gray-700 p-3 md:p-4 transition-colors duration-300">
          {/* Error Banner */}
          {error && (
            <div className="mb-3 px-3 py-2 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-2 text-xs text-red-700 dark:text-red-300 animate-slideDown">
              <AlertCircle size={14} className="shrink-0" />
              <span className="flex-1">{error}</span>
              <button
                onClick={clearError}
                className="p-1 hover:bg-red-100 dark:hover:bg-red-800 rounded transition-colors"
              >
                <span className="text-red-500">&times;</span>
              </button>
            </div>
          )}

          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              placeholder={
                files.length === 0
                  ? 'Upload a CSV file first, then ask a question...'
                  : selectedFiles.length === 0
                    ? 'Select files from sidebar, then ask a question...'
                    : 'Ask a question about your data...'
              }
              className="flex-1 border border-gray-300 dark:border-gray-600 rounded-xl px-4 py-2.5 text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 transition-all duration-200"
            />
            <button
              onClick={() => handleSend()}
              disabled={!canSend()}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 dark:disabled:bg-blue-800 text-white rounded-xl px-4 py-2.5 transition-all duration-200 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <RefreshCw size={18} className="animate-spin" />
              ) : (
                <Send size={18} />
              )}
            </button>
            {messages.length > 0 && (
              <button
                onClick={clearChat}
                disabled={isLoading}
                className="text-gray-400 dark:text-gray-500 hover:text-red-500 dark:hover:text-red-400 disabled:opacity-30 px-2 transition-colors"
                title="Clear chat history"
              >
                <Trash2 size={18} />
              </button>
            )}
          </div>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-1.5 text-center transition-colors">
            Press Enter to send · AI may take 30–40 seconds to analyze and execute code
          </p>
        </div>
      </div>

      {/* Animations */}
      <style>{`
        @keyframes fadeIn { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes slideDown { from { opacity: 0; transform: translateY(-8px); } to { opacity: 1; transform: translateY(0); } }
        .animate-fadeIn { animation: fadeIn 0.3s ease-out; }
        .animate-slideDown { animation: slideDown 0.3s ease-out; }
      `}</style>
    </div>
  );
}