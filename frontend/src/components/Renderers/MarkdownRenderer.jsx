import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';

export default function MarkdownRenderer({ content }) {
  if (!content || typeof content !== 'string') return null;

  return (
    <div className="prose prose-sm max-w-none prose-headings:text-gray-800 prose-p:text-gray-700 prose-a:text-blue-600 prose-code:text-pink-600 prose-code:bg-gray-100 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-pre:bg-gray-900 prose-pre:text-gray-100 prose-pre:rounded-lg prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-strong:text-gray-800 prose-table:text-sm prose-th:bg-gray-50 prose-th:px-3 prose-th:py-2 prose-td:px-3 prose-td:py-1.5">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
        components={{
          code({ node, inline, className, children, ...props }) {
            if (inline) {
              return (
                <code className="bg-gray-100 text-pink-600 px-1.5 py-0.5 rounded text-xs font-mono" {...props}>
                  {children}
                </code>
              );
            }
            const codeString = String(children).replace(/\n$/, '');
            return (
              <div className="relative group my-3">
                <button
                  onClick={() => navigator.clipboard.writeText(codeString)}
                  className="absolute right-2 top-2 text-xs text-gray-400 hover:text-white bg-gray-700 hover:bg-gray-600 px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  Copy
                </button>
                <pre className="bg-gray-900 text-gray-100 rounded-lg p-4 overflow-x-auto text-sm leading-relaxed">
                  <code className="text-gray-100" {...props}>{children}</code>
                </pre>
              </div>
            );
          },
          table({ children }) {
            return (
              <div className="overflow-x-auto my-3 border border-gray-200 rounded-lg">
                <table className="min-w-full divide-y divide-gray-200">{children}</table>
              </div>
            );
          },
          th({ children }) {
            return <th className="bg-gray-50 px-4 py-2.5 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider border-b border-gray-200">{children}</th>;
          },
          td({ children }) {
            return <td className="px-4 py-2 text-sm text-gray-700 border-b border-gray-100 whitespace-nowrap">{children}</td>;
          },
          blockquote({ children }) {
            return (
              <blockquote className="border-l-4 border-blue-400 pl-4 my-3 italic text-gray-600 bg-blue-50/50 py-2 pr-2 rounded-r-lg">
                {children}
              </blockquote>
            );
          },
          img({ src, alt }) {
            return (
              <img
                src={src}
                alt={alt || ''}
                className="rounded-lg max-w-full my-3 shadow-md"
                loading="lazy"
              />
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}