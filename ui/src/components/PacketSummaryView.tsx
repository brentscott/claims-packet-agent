import { useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  DollarSign,
  FileText,
  ShieldAlert,
  User,
  TrendingDown,
  ClipboardList,
  Info,
} from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Lightweight markdown-to-HTML converter for rendering LLM narrative output.
 * Handles: headers, bold, italic, numbered lists, bullet lists, paragraphs.
 */
function renderMarkdown(md: string): string {
  // Escape HTML entities
  let html = md
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Split into lines for block-level processing
  const lines = html.split("\n");
  const output: string[] = [];
  let inUl = false;
  let inOl = false;

  for (let i = 0; i < lines.length; i++) {
    let line = lines[i];

    // Close open lists if this line isn't a list item
    const isBullet = /^\s*[-*]\s+/.test(line);
    const isNumbered = /^\s*\d+[.)]\s+/.test(line);

    if (!isBullet && inUl) {
      output.push("</ul>");
      inUl = false;
    }
    if (!isNumbered && inOl) {
      output.push("</ol>");
      inOl = false;
    }

    // Headers
    if (/^####\s+(.+)/.test(line)) {
      const m = line.match(/^####\s+(.+)/);
      output.push(`<h4 class="text-sm font-semibold text-gray-800 mt-3 mb-1">${m![1]}</h4>`);
      continue;
    }
    if (/^###\s+(.+)/.test(line)) {
      const m = line.match(/^###\s+(.+)/);
      output.push(`<h3 class="text-base font-semibold text-gray-900 mt-4 mb-1">${m![1]}</h3>`);
      continue;
    }
    if (/^##\s+(.+)/.test(line)) {
      const m = line.match(/^##\s+(.+)/);
      output.push(`<h2 class="text-lg font-semibold text-gray-900 mt-4 mb-1">${m![1]}</h2>`);
      continue;
    }
    if (/^#\s+(.+)/.test(line)) {
      const m = line.match(/^#\s+(.+)/);
      output.push(`<h1 class="text-xl font-bold text-gray-900 mt-4 mb-1">${m![1]}</h1>`);
      continue;
    }

    // Bullet list items
    if (isBullet) {
      if (!inUl) {
        output.push('<ul class="list-disc pl-5 space-y-1 my-2">');
        inUl = true;
      }
      const content = line.replace(/^\s*[-*]\s+/, "");
      output.push(`<li>${applyInline(content)}</li>`);
      continue;
    }

    // Numbered list items
    if (isNumbered) {
      if (!inOl) {
        output.push('<ol class="list-decimal pl-5 space-y-1 my-2">');
        inOl = true;
      }
      const content = line.replace(/^\s*\d+[.)]\s+/, "");
      output.push(`<li>${applyInline(content)}</li>`);
      continue;
    }

    // Blank lines become paragraph breaks
    if (line.trim() === "") {
      output.push('<div class="h-2"></div>');
      continue;
    }

    // Regular paragraph line
    output.push(`<p class="my-1">${applyInline(line)}</p>`);
  }

  // Close any open lists
  if (inUl) output.push("</ul>");
  if (inOl) output.push("</ol>");

  return output.join("\n");
}

/** Apply inline markdown: bold, italic, inline code */
function applyInline(text: string): string {
  return text
    // Bold + italic: ***text***
    .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
    // Bold: **text**
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // Italic: *text*
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // Inline code: `text`
    .replace(/`(.+?)`/g, '<code class="bg-gray-100 px-1 py-0.5 rounded text-xs">$1</code>');
}

// --- Types matching the Python ClaimsPacketOutput ---

interface PatientInfo {
  first_name?: string | null;
  last_name?: string | null;
  date_of_birth?: string | null;
  member_id?: string | null;
  group_number?: string | null;
  address?: string | null;
}

interface ValidationResult {
  check_name: string;
  status: string;
  severity: "HIGH" | "MEDIUM" | "LOW" | "INFO";
  detail: string;
  potential_overcharge?: number | null;
  recommendation?: string | null;
}

interface FinancialSummary {
  total_billed?: number | null;
  total_allowed?: number | null;
  total_insurance_paid?: number | null;
  total_patient_responsibility_per_eob?: number | null;
  total_patient_responsibility_per_bills?: number | null;
  discrepancy_amount?: number | null;
  potential_savings?: number | null;
  flagged_issues?: number;
}

interface DocumentEnvelope {
  doc_id: string;
  file_id?: string | null;
  filename: string;
  classified_type: string;
  classification_confidence: number;
  field_confidence?: Record<string, number>;
  extraction_warnings?: string[];
}

interface ProcessedDocument {
  envelope: DocumentEnvelope;
  extracted_data: Record<string, unknown>;
  schema_used: string;
}

export interface ClaimsPacketData {
  packet_id: string;
  patient: PatientInfo;
  documents: ProcessedDocument[];
  validation_results: ValidationResult[];
  financial_summary: FinancialSummary;
  recommended_actions: string[];
  summary_narrative?: string | null;
}

/**
 * Check if item data contains a claims packet output (vs generic extracted data).
 */
export function isClaimsPacket(data: unknown): data is ClaimsPacketData {
  if (!data || typeof data !== "object") return false;
  const d = data as Record<string, unknown>;
  return (
    typeof d.packet_id === "string" &&
    Array.isArray(d.documents) &&
    Array.isArray(d.validation_results) &&
    d.financial_summary !== undefined
  );
}

// --- Helper Components ---

function formatCurrency(value: number | null | undefined): string {
  if (value == null) return "N/A";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(value);
}

function SeverityBadge({ severity }: { severity: string }) {
  const config: Record<string, { bg: string; text: string; label: string }> = {
    HIGH: {
      bg: "bg-red-100",
      text: "text-red-800",
      label: "Critical",
    },
    MEDIUM: {
      bg: "bg-yellow-100",
      text: "text-yellow-800",
      label: "Important",
    },
    LOW: {
      bg: "bg-blue-100",
      text: "text-blue-800",
      label: "Low",
    },
    INFO: {
      bg: "bg-gray-100",
      text: "text-gray-700",
      label: "Info",
    },
  };

  const c = config[severity] || config.INFO;
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        c.bg,
        c.text,
      )}
    >
      {c.label}
    </span>
  );
}

function StatCard({
  label,
  value,
  icon: Icon,
  highlight,
}: {
  label: string;
  value: string;
  icon: React.ComponentType<{ className?: string }>;
  highlight?: "red" | "green" | "yellow" | null;
}) {
  const borderColor =
    highlight === "red"
      ? "border-red-300"
      : highlight === "green"
        ? "border-green-300"
        : highlight === "yellow"
          ? "border-yellow-300"
          : "border-gray-200";

  return (
    <div
      className={cn(
        "rounded-lg border p-4 bg-white shadow-sm",
        borderColor,
      )}
    >
      <div className="flex items-center gap-2 mb-1">
        <Icon className="h-4 w-4 text-gray-500" />
        <span className="text-xs text-gray-500 uppercase tracking-wide">
          {label}
        </span>
      </div>
      <div className="text-xl font-semibold text-gray-900">{value}</div>
    </div>
  );
}

function CollapsibleSection({
  title,
  icon: Icon,
  children,
  defaultOpen = true,
  badge,
}: {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
  defaultOpen?: boolean;
  badge?: React.ReactNode;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="border border-gray-200 rounded-lg bg-white shadow-sm">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center gap-2 px-4 py-3 text-left hover:bg-gray-50 transition-colors"
      >
        {isOpen ? (
          <ChevronDown className="h-4 w-4 text-gray-400 shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 text-gray-400 shrink-0" />
        )}
        <Icon className="h-4 w-4 text-gray-600 shrink-0" />
        <span className="font-medium text-gray-900 text-sm">{title}</span>
        {badge && <div className="ml-auto">{badge}</div>}
      </button>
      {isOpen && <div className="px-4 pb-4 border-t border-gray-100">{children}</div>}
    </div>
  );
}

// --- Main Component ---

export function PacketSummaryView({ data }: { data: ClaimsPacketData }) {
  const {
    patient,
    documents,
    validation_results,
    financial_summary,
    recommended_actions,
    summary_narrative,
    packet_id,
  } = data;

  const highCount = validation_results.filter(
    (r) => r.severity === "HIGH",
  ).length;
  const mediumCount = validation_results.filter(
    (r) => r.severity === "MEDIUM",
  ).length;
  const passCount = validation_results.filter(
    (r) => r.status === "PASS",
  ).length;

  const patientName = [patient.first_name, patient.last_name]
    .filter(Boolean)
    .join(" ");

  return (
    <div className="space-y-4 p-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">
            Claims Packet Analysis
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {patientName || "Patient"} &middot; {documents.length} document
            {documents.length !== 1 ? "s" : ""} processed
          </p>
        </div>
        {highCount > 0 && (
          <div className="flex items-center gap-1.5 bg-red-50 text-red-700 rounded-full px-3 py-1.5 text-sm font-medium">
            <ShieldAlert className="h-4 w-4" />
            {highCount} critical issue{highCount !== 1 ? "s" : ""} found
          </div>
        )}
      </div>

      {/* Patient Info Bar */}
      {patientName && (
        <div className="flex items-center gap-4 bg-gray-50 rounded-lg px-4 py-3 text-sm">
          <div className="flex items-center gap-1.5">
            <User className="h-4 w-4 text-gray-500" />
            <span className="font-medium">{patientName}</span>
          </div>
          {patient.member_id && (
            <span className="text-gray-500">
              ID: {patient.member_id}
            </span>
          )}
          {patient.date_of_birth && (
            <span className="text-gray-500">
              DOB: {patient.date_of_birth}
            </span>
          )}
          {patient.group_number && (
            <span className="text-gray-500">
              Group: {patient.group_number}
            </span>
          )}
        </div>
      )}

      {/* Financial Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard
          label="Total Billed"
          value={formatCurrency(financial_summary.total_billed)}
          icon={DollarSign}
        />
        <StatCard
          label="Insurance Paid"
          value={formatCurrency(financial_summary.total_insurance_paid)}
          icon={DollarSign}
          highlight="green"
        />
        <StatCard
          label="Your Responsibility (EOB)"
          value={formatCurrency(
            financial_summary.total_patient_responsibility_per_eob,
          )}
          icon={DollarSign}
        />
        <StatCard
          label="Potential Savings"
          value={formatCurrency(financial_summary.potential_savings)}
          icon={TrendingDown}
          highlight={
            financial_summary.potential_savings &&
            financial_summary.potential_savings > 0
              ? "green"
              : null
          }
        />
      </div>

      {/* Discrepancy Alert */}
      {financial_summary.discrepancy_amount != null &&
        financial_summary.discrepancy_amount > 0 && (
          <div className="flex items-start gap-3 bg-red-50 border border-red-200 rounded-lg p-4">
            <AlertTriangle className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-red-800">
                Billing Discrepancy Detected
              </p>
              <p className="text-sm text-red-700 mt-0.5">
                Provider bills total{" "}
                {formatCurrency(
                  financial_summary.total_patient_responsibility_per_bills,
                )}{" "}
                but your EOB says you owe{" "}
                {formatCurrency(
                  financial_summary.total_patient_responsibility_per_eob,
                )}
                . That&apos;s a{" "}
                <strong>
                  {formatCurrency(financial_summary.discrepancy_amount)}
                </strong>{" "}
                difference.
              </p>
            </div>
          </div>
        )}

      {/* Summary Narrative */}
      {summary_narrative && (
        <CollapsibleSection
          title="Analysis Summary"
          icon={ClipboardList}
          defaultOpen={true}
        >
          <div
            className="prose prose-sm max-w-none mt-3 text-gray-700 leading-relaxed"
            dangerouslySetInnerHTML={{ __html: renderMarkdown(summary_narrative) }}
          />
        </CollapsibleSection>
      )}

      {/* Recommended Actions */}
      {recommended_actions.length > 0 && (
        <CollapsibleSection
          title="Recommended Actions"
          icon={ClipboardList}
          defaultOpen={true}
          badge={
            <span className="text-xs bg-blue-100 text-blue-800 rounded-full px-2 py-0.5">
              {recommended_actions.length}
            </span>
          }
        >
          <ol className="mt-3 space-y-2">
            {recommended_actions.map((action, i) => {
              const isUrgent = action.startsWith("URGENT:");
              return (
                <li
                  key={i}
                  className={cn(
                    "flex items-start gap-2 text-sm rounded-lg px-3 py-2",
                    isUrgent ? "bg-red-50" : "bg-gray-50",
                  )}
                >
                  <span
                    className={cn(
                      "font-mono text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center shrink-0 mt-0.5",
                      isUrgent
                        ? "bg-red-200 text-red-800"
                        : "bg-blue-200 text-blue-800",
                    )}
                  >
                    {i + 1}
                  </span>
                  <span
                    className={cn(
                      isUrgent ? "text-red-800" : "text-gray-700",
                    )}
                  >
                    {action}
                  </span>
                </li>
              );
            })}
          </ol>
        </CollapsibleSection>
      )}

      {/* Validation Results */}
      <CollapsibleSection
        title="Validation Findings"
        icon={ShieldAlert}
        defaultOpen={highCount > 0 || mediumCount > 0}
        badge={
          <div className="flex items-center gap-2">
            {highCount > 0 && (
              <span className="text-xs bg-red-100 text-red-800 rounded-full px-2 py-0.5">
                {highCount} critical
              </span>
            )}
            {mediumCount > 0 && (
              <span className="text-xs bg-yellow-100 text-yellow-800 rounded-full px-2 py-0.5">
                {mediumCount} important
              </span>
            )}
            {passCount > 0 && (
              <span className="text-xs bg-green-100 text-green-800 rounded-full px-2 py-0.5">
                {passCount} passed
              </span>
            )}
          </div>
        }
      >
        <div className="mt-3 space-y-2">
          {validation_results.length === 0 ? (
            <div className="flex items-center gap-2 text-sm text-green-700 bg-green-50 rounded-lg px-3 py-2">
              <CheckCircle2 className="h-4 w-4" />
              All validation checks passed — no issues found.
            </div>
          ) : (
            validation_results.map((result, i) => (
              <div
                key={i}
                className={cn(
                  "rounded-lg px-3 py-3 text-sm border",
                  result.severity === "HIGH"
                    ? "bg-red-50 border-red-200"
                    : result.severity === "MEDIUM"
                      ? "bg-yellow-50 border-yellow-200"
                      : result.status === "PASS"
                        ? "bg-green-50 border-green-200"
                        : "bg-gray-50 border-gray-200",
                )}
              >
                <div className="flex items-center gap-2 mb-1">
                  <SeverityBadge severity={result.severity} />
                  <span className="font-mono text-xs text-gray-500">
                    {result.check_name}
                  </span>
                  {result.potential_overcharge != null &&
                    result.potential_overcharge > 0 && (
                      <span className="ml-auto text-xs font-medium text-red-700">
                        {formatCurrency(result.potential_overcharge)} at risk
                      </span>
                    )}
                </div>
                <p className="text-gray-700 mt-1">{result.detail}</p>
                {result.recommendation && (
                  <p className="text-gray-600 mt-1 text-xs italic">
                    {result.recommendation}
                  </p>
                )}
              </div>
            ))
          )}
        </div>
      </CollapsibleSection>

      {/* Documents Processed */}
      <CollapsibleSection
        title="Documents Processed"
        icon={FileText}
        defaultOpen={false}
        badge={
          <span className="text-xs bg-gray-100 text-gray-700 rounded-full px-2 py-0.5">
            {documents.length}
          </span>
        }
      >
        <div className="mt-3 space-y-2">
          {documents.map((doc, i) => (
            <div
              key={i}
              className="flex items-center gap-3 text-sm bg-gray-50 rounded-lg px-3 py-2"
            >
              <FileText className="h-4 w-4 text-gray-400 shrink-0" />
              <div className="flex-1 min-w-0">
                <span className="font-medium text-gray-900 truncate block">
                  {doc.envelope.filename}
                </span>
              </div>
              <span className="text-xs bg-blue-100 text-blue-800 rounded px-1.5 py-0.5">
                {doc.envelope.classified_type}
              </span>
              <span className="text-xs text-gray-500">
                {(doc.envelope.classification_confidence * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      </CollapsibleSection>

      {/* Per-Document Extracted Data */}
      {documents.map((doc, i) => {
        const docData = doc.extracted_data;
        if (!docData || Object.keys(docData).length === 0) return null;

        return (
          <CollapsibleSection
            key={i}
            title={`${doc.envelope.filename} — Extracted Fields`}
            icon={Info}
            defaultOpen={false}
          >
            <div className="mt-3">
              <pre className="text-xs bg-gray-50 rounded-lg p-3 overflow-auto max-h-96 text-gray-700">
                {JSON.stringify(docData, null, 2)}
              </pre>
            </div>
          </CollapsibleSection>
        );
      })}
    </div>
  );
}
