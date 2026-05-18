import React from 'react';
import { Menu, Moon, Sun, Activity } from 'lucide-react';
import useAppStore from '../../store/useAppStore';

export default function Topbar({ onToggleSidebar, darkMode, onToggleDarkMode }) {
  const { files, selectedFiles } = useAppStore();

  const status = files.length > 0
    ? (selectedFiles.length > 0 ? 'ready' : 'idle')
    : 'empty';

  return (
    <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 px-4 py-2.5 flex items-center shadow-sm shrink-0 transition-colors">
      {/* Sidebar toggle */}
      <button
        onClick={onToggleSidebar}
        className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400 mr-3 transition-colors"
        title="Toggle sidebar"
      >
        <Menu size={20} />
      </button>

      {/* App title */}
      <h1 className="text-lg font-bold text-gray-800 dark:text-gray-100 mr-8 hidden sm:block tracking-tight">
        AI Data Analyst
      </h1>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Session status indicator */}
      <div className="flex items-center gap-1.5 text-xs text-gray-400 dark:text-gray-500 mr-3">
        <Activity size={12} />
        <span
          className={`inline-block w-2 h-2 rounded-full ${
            status === 'ready'
              ? 'bg-green-500'
              : status === 'idle'
                ? 'bg-yellow-400'
                : 'bg-gray-300'
          }`}
        />
        <span className="hidden sm:inline">
          {status === 'ready'
            ? 'Ready'
            : status === 'idle'
              ? 'Files loaded'
              : 'No data'}
        </span>
      </div>

      {/* Theme toggle */}
      <button
        onClick={onToggleDarkMode}
        className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400 transition-colors"
        title={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
      >
        {darkMode ? <Sun size={18} /> : <Moon size={18} />}
      </button>
    </header>
  );
}