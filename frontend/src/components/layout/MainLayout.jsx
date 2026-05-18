import React, { useState, useEffect, useCallback } from 'react';
import { PanelRightOpen } from 'lucide-react';
import Sidebar from './Sidebar';
import Topbar from './Topbar';
import ChatInterface from '../chat/ChatInterface';
import RightPanel from './RightPanel';
import ReviewModal from '../Feedback/ReviewModal';
import useAppStore from '../../store/useAppStore';

export default function MainLayout() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isRightPanelOpen, setIsRightPanelOpen] = useState(false);
  const [rightPanelHeight, setRightPanelHeight] = useState(40); // percentage

  const {
    theme,
    toggleTheme,
    messages,
    files,
    selectedFiles,
  } = useAppStore();

  // Apply theme from store
  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
  }, [theme]);

  // Auto-open right panel when AI returns charts
  useEffect(() => {
    const lastMsg = messages[messages.length - 1];
    if (lastMsg?.role === 'ai' && lastMsg?.files?.length > 0) {
      setIsRightPanelOpen(true);
    }
  }, [messages]);

  // Handle "Analyze" button in sidebar
  const handleAnalyze = useCallback(() => {
    if (selectedFiles.length === 0) return;
    const chatInput = document.querySelector('input[placeholder*="Ask a question"]');
    if (chatInput) {
      chatInput.focus();
    }
  }, [selectedFiles]);

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-950 text-gray-800 dark:text-gray-200 transition-colors duration-300">
      {/* Left Sidebar */}
      <Sidebar
        isOpen={isSidebarOpen}
        setIsOpen={setIsSidebarOpen}
        onAnalyze={handleAnalyze}
      />

      {/* Main content area */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        {/* Top navbar */}
        <Topbar
          onToggleSidebar={() => setIsSidebarOpen(prev => !prev)}
          darkMode={theme === 'dark'}
          onToggleDarkMode={toggleTheme}
        />

        {/* Main content: Chat (top) + Right Panel (bottom) */}
        <div className="flex-1 flex flex-col overflow-hidden p-4 lg:p-6 gap-4">
          {/* Chat area — takes remaining space */}
          <div className="flex-1 min-h-0">
            <ChatInterface darkMode={theme === 'dark'} />
          </div>

          {/* Right panel toggle button */}
          {!isRightPanelOpen && (
            <div className="flex justify-center">
              <button
                onClick={() => setIsRightPanelOpen(true)}
                className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-medium
                  bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400
                  hover:bg-gray-200 dark:hover:bg-gray-700
                  rounded-full transition-colors border border-gray-200 dark:border-gray-700"
              >
                <PanelRightOpen size={14} />
                Show Data & Charts
              </button>
            </div>
          )}

          {/* Right panel (resizable) */}
          {isRightPanelOpen && (
            <div
              className="shrink-0 flex flex-col"
              style={{ height: `${rightPanelHeight}%` }}
            >
              {/* Resize handle */}
              <div
                className="h-1.5 cursor-row-resize hover:bg-blue-400/30 active:bg-blue-500/50 rounded-full transition-colors -mb-1 z-10"
                onMouseDown={(e) => {
                  const startY = e.clientY;
                  const startH = rightPanelHeight;
                  const container = e.currentTarget.parentElement?.parentElement;
                  const containerHeight = container?.clientHeight || 600;

                  const onMouseMove = (moveEvent) => {
                    const deltaY = startY - moveEvent.clientY;
                    const deltaPercent = (deltaY / containerHeight) * 100;
                    const newH = Math.min(70, Math.max(20, startH + deltaPercent));
                    setRightPanelHeight(newH);
                  };

                  const onMouseUp = () => {
                    document.removeEventListener('mousemove', onMouseMove);
                    document.removeEventListener('mouseup', onMouseUp);
                  };

                  document.addEventListener('mousemove', onMouseMove);
                  document.addEventListener('mouseup', onMouseUp);
                }}
              />

              {/* Right panel content */}
              <div className="flex-1 min-h-0 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden bg-white dark:bg-gray-900 shadow-sm">
                <RightPanel
                  onClose={() => setIsRightPanelOpen(false)}
                  isCollapsed={false}
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Review Modal */}
      <ReviewModal />
    </div>
  );
}