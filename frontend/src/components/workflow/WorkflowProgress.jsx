// src/components/workflow/WorkflowProgress.jsx
// Live panel that shows the steps the backend is currently performing
// while a chat request is in flight: waiting on AI, querying the
// database, running code in E2B, etc.

import React from 'react';
import {
  Brain, Database, Code2, AlertTriangle, CheckCircle2, Loader2, ListChecks,
} from 'lucide-react';
import useAppStore from '../../store/useAppStore';

const STAGE_META = {
  init:            { label: 'Initialising',          icon: ListChecks },
  calling_llm:     { label: 'Calling AI',            icon: Brain },
  llm:             { label: 'AI thinking',           icon: Brain },
  data_context:    { label: 'Reading data context',  icon: Database },
  describe_database: { label: 'Describing database', icon: Database },
  query_db:        { label: 'Querying database',     icon: Database },
  e2b:             { label: 'Running code',          icon: Code2 },
  final:           { label: 'Finalising',            icon: CheckCircle2 },
  parse:           { label: 'Parsing response',      icon: Brain },
};

function statusFromType(type) {
  if (type === 'done') return 'done';
  if (type === 'error' || type === 'tool_giveup') return 'error';
  if (type === 'warning') return 'warn';
  return 'done';
}

function StageIcon({ type, status }) {
  if (status === 'error') return <AlertTriangle size={14} className="text-red-500" />;
  if (status === 'warn')  return <AlertTriangle size={14} className="text-amber-500" />;
  if (status === 'done')  return <CheckCircle2 size={14} className="text-emerald-500" />;
  return <Loader2 size={14} className="text-blue-500 animate-spin" />;
}

export default function WorkflowProgress() {
  const steps = useAppStore((s) => s.workflowSteps) || [];
  const isLoading = useAppStore((s) => s.isLoading);

  if (!isLoading && steps.length === 0) {
    return null;
  }

  return (
    <div className="border border-blue-200 dark:border-blue-800 bg-blue-50/40 dark:bg-blue-900/20 rounded-xl p-3 text-left">
      <div className="flex items-center gap-2 mb-2">
        {isLoading ? (
          <Loader2 size={14} className="text-blue-500 animate-spin" />
        ) : (
          <CheckCircle2 size={14} className="text-emerald-500" />
        )}
        <p className="text-xs font-semibold text-blue-700 dark:text-blue-300 uppercase tracking-wider">
          {isLoading ? 'Workflow in progress' : 'Workflow complete'}
        </p>
      </div>

      {steps.length === 0 && isLoading && (
        <div className="flex items-center gap-2 text-xs text-blue-700 dark:text-blue-300">
          <Loader2 size={12} className="animate-spin" />
          <span>Sending request to the backend...</span>
        </div>
      )}

      {steps.length > 0 && (
        <ol className="space-y-1.5">
          {steps.map((step, idx) => {
            const meta = STAGE_META[step.stage] || { label: step.stage || 'Working...', icon: Brain };
            const isLast = idx === steps.length - 1;
            const status = step.status || statusFromType(step.type);
            return (
              <li key={step.id || idx} className="flex items-start gap-2 text-xs">
                <div className="mt-0.5 shrink-0">
                  <StageIcon type={step.type} status={status} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="font-medium text-gray-700 dark:text-gray-200">
                      {meta.label}
                    </span>
                    {!isLast && (
                      <span className="text-[10px] text-gray-400 dark:text-gray-500">
                        step {idx + 1}
                      </span>
                    )}
                  </div>
                  {step.label && step.label !== meta.label && (
                    <p className="text-[11px] text-gray-500 dark:text-gray-400 leading-snug mt-0.5">
                      {step.label}
                    </p>
                  )}
                  {step.detail && (
                    <pre className="mt-1 text-[10px] font-mono text-gray-500 dark:text-gray-400 bg-white/60 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 rounded p-1.5 overflow-x-auto max-h-24 whitespace-pre-wrap break-words">
                      {step.detail}
                    </pre>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      )}

      {isLoading && steps.length > 0 && (
        <div className="mt-3 flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '0ms' }} />
          <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '150ms' }} />
          <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '300ms' }} />
          <span className="text-[10px] text-blue-600 dark:text-blue-300 ml-1">
            AI is working, this can take 30-60 seconds on the free tier
          </span>
        </div>
      )}
    </div>
  );
}
