import {
  useHandlers,
  WorkflowEvent,
  StreamOperation,
  HandlerState,
} from "@llamaindex/ui";
import { useEffect, useRef, useState } from "react";
import {
  Loader2,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { cn } from "./utils";

interface StatusMessage {
  type: "Status";
  data: {
    level: "info" | "warning" | "error";
    message: string;
  };
}

interface LogEntry {
  id: number;
  level: "info" | "warning" | "error";
  message: string;
  timestamp: Date;
}

/**
 * Given a workflow type, keeps track of the number of running handlers and the maximum number of running handlers.
 * Has hooks to notify when a workflow handler is completed.
 * Shows a scrollable log of all status messages during processing.
 */
export const WorkflowProgress = ({
  workflowName,
  onWorkflowCompletion,
  handlers = [],
  sync = true,
}: {
  workflowName: string;
  onWorkflowCompletion?: (handlerIds: string[]) => void;
  handlers?: HandlerState[];
  sync?: boolean;
}) => {
  const handlersService = useHandlers({
    query: { workflow_name: [workflowName], status: ["running"] },
    sync: sync,
  });
  const seenHandlers = useRef<Set<string>>(new Set());
  useEffect(() => {
    for (const handler of handlers) {
      if (!seenHandlers.current.has(handler.handler_id)) {
        seenHandlers.current.add(handler.handler_id);
        handlersService.setHandler(handler);
      }
    }
  }, [handlers, handlersService]);

  const subscribed = useRef<Record<string, StreamOperation<WorkflowEvent>>>(
    {},
  );

  // Log of all status messages
  const [logEntries, setLogEntries] = useState<LogEntry[]>([]);
  const logIdRef = useRef(0);
  const [isExpanded, setIsExpanded] = useState(true);
  const logEndRef = useRef<HTMLDivElement>(null);

  const [hasHadRunning, setHasHadRunning] = useState(false);

  const runningHandlers = Object.values(handlersService.state.handlers).filter(
    (handler) => handler.status === "running",
  );
  const runningHandlersKey = runningHandlers
    .map((handler) => handler.handler_id)
    .sort()
    .join(",");

  // subscribe to all running handlers and disconnect when they complete
  useEffect(() => {
    for (const handler of runningHandlers) {
      if (!subscribed.current[handler.handler_id]) {
        subscribed.current[handler.handler_id] = handlersService
          .actions(handler.handler_id)
          .subscribeToEvents({
            onComplete() {
              subscribed.current[handler.handler_id]?.disconnect();
              delete subscribed.current[handler.handler_id];
            },
            onData(data) {
              if (data.type === "StatusEvent") {
                const statusData = data.data as StatusMessage["data"];
                setLogEntries((prev) => [
                  ...prev,
                  {
                    id: ++logIdRef.current,
                    level: statusData.level,
                    message: statusData.message,
                    timestamp: new Date(),
                  },
                ]);
              }
            },
          });
      }
    }
  }, [runningHandlersKey]);

  const lastHandlers = useRef<string[]>([]);
  useEffect(() => {
    const newRunningHandlers = runningHandlers.map(
      (handler) => handler.handler_id,
    );
    const anyRemoved = lastHandlers.current.some(
      (handler) => !newRunningHandlers.includes(handler),
    );
    if (anyRemoved) {
      onWorkflowCompletion?.(lastHandlers.current);
    }
    lastHandlers.current = newRunningHandlers;
  }, [runningHandlersKey]);

  // unsubscribe on unmount
  useEffect(() => {
    return () => {
      for (const [key, handler] of Object.entries(subscribed.current)) {
        handler.disconnect();
        delete subscribed.current[key];
      }
    };
  }, []);

  // Auto-scroll to bottom of log when new entries arrive
  useEffect(() => {
    if (logEndRef.current && isExpanded) {
      logEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logEntries.length, isExpanded]);

  // Track if we've ever had any running workflows in this session
  useEffect(() => {
    if (runningHandlers.length > 0 && !hasHadRunning) {
      setHasHadRunning(true);
    }
  }, [runningHandlers.length, hasHadRunning]);

  if (!runningHandlers.length && !hasHadRunning) {
    return null;
  }

  const isRunning = runningHandlers.length > 0;
  const latestEntry =
    logEntries.length > 0 ? logEntries[logEntries.length - 1] : null;

  return (
    <div className="w-full rounded-lg border border-border bg-white shadow-sm overflow-hidden">
      {/* Header bar - always visible, clickable to expand/collapse */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-2 px-3 py-2 text-xs hover:bg-gray-50 transition-colors"
      >
        {isRunning ? (
          <Loader2
            className="h-3.5 w-3.5 animate-spin text-blue-500 shrink-0"
            aria-hidden="true"
          />
        ) : (
          <CheckCircle2
            className="h-3.5 w-3.5 text-green-500 shrink-0"
            aria-hidden="true"
          />
        )}

        <span className="font-medium text-gray-700">
          {isRunning
            ? `Processing${runningHandlers.length > 1 ? ` (${runningHandlers.length} workflows)` : ""}...`
            : "Processing complete"}
        </span>

        {/* Show latest message in collapsed view */}
        {!isExpanded && latestEntry && (
          <span
            className={cn(
              "ml-1 truncate text-gray-500",
              latestEntry.level === "error" && "text-red-500",
              latestEntry.level === "warning" && "text-yellow-600",
            )}
          >
            {latestEntry.message}
          </span>
        )}

        <div className="ml-auto flex items-center gap-1.5 shrink-0">
          {logEntries.length > 0 && (
            <span className="text-gray-400">
              {logEntries.length} step{logEntries.length !== 1 ? "s" : ""}
            </span>
          )}
          {isExpanded ? (
            <ChevronUp className="h-3.5 w-3.5 text-gray-400" />
          ) : (
            <ChevronDown className="h-3.5 w-3.5 text-gray-400" />
          )}
        </div>
      </button>

      {/* Expanded log view */}
      {isExpanded && logEntries.length > 0 && (
        <div className="border-t border-gray-100 max-h-48 overflow-y-auto px-3 py-2 space-y-1 bg-gray-50">
          {logEntries.map((entry) => (
            <div
              key={entry.id}
              className="flex items-start gap-2 text-xs animate-in fade-in slide-in-from-bottom-1 duration-200"
            >
              {/* Icon */}
              {entry.level === "error" ? (
                <XCircle className="h-3.5 w-3.5 text-red-500 shrink-0 mt-0.5" />
              ) : entry.level === "warning" ? (
                <AlertTriangle className="h-3.5 w-3.5 text-yellow-500 shrink-0 mt-0.5" />
              ) : (
                <CheckCircle2 className="h-3.5 w-3.5 text-green-500 shrink-0 mt-0.5" />
              )}

              {/* Message */}
              <span
                className={cn(
                  "flex-1",
                  entry.level === "error"
                    ? "text-red-700"
                    : entry.level === "warning"
                      ? "text-yellow-700"
                      : "text-gray-700",
                )}
              >
                {entry.message}
              </span>

              {/* Timestamp */}
              <span className="text-gray-400 shrink-0 tabular-nums">
                {entry.timestamp.toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                  second: "2-digit",
                })}
              </span>
            </div>
          ))}

          {/* Scroll anchor */}
          <div ref={logEndRef} />

          {/* Active spinner at bottom when still running */}
          {isRunning && (
            <div className="flex items-center gap-2 text-xs text-gray-400 pt-1">
              <Loader2 className="h-3 w-3 animate-spin" />
              <span>Waiting for next step...</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
