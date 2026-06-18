// src/components/ErrorBoundary.jsx
// Lightweight React error boundary that renders the caught error
// on screen so a failed render does not result in a blank page.

import React from 'react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, info: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    // Persist the full error on state so the user can read it.
    this.setState({ info });
    // Also log to the console for browser dev tools.
    // eslint-disable-next-line no-console
    console.error('ErrorBoundary caught:', error, info);
  }

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }
    const err = this.state.error;
    const message = (err && (err.message || err.toString())) || 'Unknown error';
    const stack = (err && err.stack) || '';

    return (
      <div className="min-h-screen w-full flex items-center justify-center bg-gray-50 dark:bg-gray-950 text-gray-800 dark:text-gray-100 p-6">
        <div className="max-w-2xl w-full bg-white dark:bg-gray-900 border border-red-200 dark:border-red-800 rounded-2xl shadow-lg p-6">
          <h1 className="text-xl font-semibold text-red-600 dark:text-red-400 mb-2">
            The page failed to render
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            An error happened while loading the application. The detail
            below is shown so it can be reported or fixed.
          </p>
          <pre className="text-xs bg-gray-900 text-red-300 p-3 rounded-md overflow-x-auto max-h-60 whitespace-pre-wrap break-words">
            {message}
          </pre>
          {stack && (
            <pre className="mt-3 text-[10px] bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 p-3 rounded-md overflow-x-auto max-h-72 whitespace-pre-wrap break-words">
              {stack}
            </pre>
          )}
        </div>
      </div>
    );
  }
}
