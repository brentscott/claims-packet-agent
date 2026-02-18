import {
  ItemCount,
  WorkflowTrigger,
  ExtractedDataItemGrid,
  HandlerState,
  AgentDataItem,
} from "@llamaindex/ui";
import styles from "./HomePage.module.css";
import { useNavigate } from "react-router-dom";
import { useState } from "react";
import { WorkflowProgress } from "@/lib/WorkflowProgress";
import { FileText, AlertTriangle, ShieldAlert, CheckCircle2 } from "lucide-react";
import type { ClaimsPacketData } from "@/components/PacketSummaryView";

/** Extract the nested packet data from an AgentDataItem. */
function getPacketData(item: AgentDataItem): ClaimsPacketData | null {
  const d = (item.data as Record<string, unknown>)?.data;
  if (d && typeof d === "object" && "patient" in d) return d as ClaimsPacketData;
  return null;
}

/** Build a human-readable packet name from patient + doc info. */
function getPacketLabel(item: AgentDataItem): string {
  const pkt = getPacketData(item);
  if (!pkt) return item.id ?? "Unknown Packet";

  const parts: string[] = [];

  // Patient name (Last, First)
  const last = pkt.patient?.last_name?.trim();
  const first = pkt.patient?.first_name?.trim();
  if (last || first) {
    parts.push([last, first].filter(Boolean).join(", "));
  }

  // Dominant doc type summary (e.g., "3 bills, 1 EOB")
  if (Array.isArray(pkt.documents) && pkt.documents.length > 0) {
    const typeCounts: Record<string, number> = {};
    for (const doc of pkt.documents) {
      const t = doc.envelope?.classified_type ?? "UNKNOWN";
      const label = t.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase());
      typeCounts[label] = (typeCounts[label] || 0) + 1;
    }
    const summary = Object.entries(typeCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([t, n]) => `${n} ${t}`)
      .join(", ");
    parts.push(`(${summary})`);
  }

  return parts.length > 0 ? parts.join(" ") : item.id ?? "Unknown Packet";
}

export default function HomePage() {
  return <TaskList />;
}

function TaskList() {
  const navigate = useNavigate();
  const goToItem = (item: AgentDataItem) => {
    navigate(`/item/${item.id}`);
  };
  const [reloadSignal, setReloadSignal] = useState(0);
  const [handlers, setHandlers] = useState<HandlerState[]>([]);

  return (
    <div className={styles.page}>
      <main className={styles.main}>
        <div className={styles.grid}>
          <ItemCount
            title="Total Packets"
            key={`total-items-${reloadSignal}`}
          />
          <ItemCount
            title="Reviewed"
            filter={{
              status: { includes: ["approved", "rejected"] },
            }}
            key={`reviewed-${reloadSignal}`}
          />
          <ItemCount
            title="Needs Review"
            filter={{
              status: { eq: "pending_review" },
            }}
            key={`needs-review-${reloadSignal}`}
          />
        </div>
        <div className={styles.commandBar}>
          <WorkflowProgress
            workflowName="process-file"
            handlers={handlers}
            onWorkflowCompletion={() => {
              setReloadSignal(reloadSignal + 1);
            }}
          />
          <WorkflowTrigger
            workflowName="process-file"
            multiple={true}
            contentHash={{ enabled: true }}
            customWorkflowInput={(files) => {
              return {
                file_ids: files.map((file) => file.fileId),
              };
            }}
            onSuccess={(handler) => {
              setHandlers([...handlers, handler]);
            }}
          />
        </div>

        <ExtractedDataItemGrid
          key={reloadSignal}
          onRowClick={goToItem}
          builtInColumns={{
            fileName: {
              header: "Packet Name",
              getValue: (item: AgentDataItem) => getPacketLabel(item),
              renderCell: (value: unknown) => (
                <span className="font-medium text-gray-900 text-sm">
                  {value as string}
                </span>
              ),
            },
            status: true,
            createdAt: true,
            itemsToReview: {
              header: "Documents",
              getValue: (item: AgentDataItem) => {
                const pkt = getPacketData(item);
                return pkt?.documents?.length ?? 0;
              },
              renderCell: (value: unknown) => {
                const count = value as number;
                return (
                  <span className="inline-flex items-center gap-1 text-xs text-gray-600">
                    <FileText className="h-3 w-3" />
                    {count} file{count !== 1 ? "s" : ""}
                  </span>
                );
              },
            },
            actions: true,
          }}
          customColumns={[
            {
              key: "findings",
              header: "Findings",
              getValue: (item: AgentDataItem) => {
                const pkt = getPacketData(item);
                if (!pkt?.validation_results) return { high: 0, medium: 0, low: 0, info: 0 };
                const counts = { high: 0, medium: 0, low: 0, info: 0 };
                for (const r of pkt.validation_results) {
                  const sev = (r.severity || "").toUpperCase();
                  if (sev === "HIGH") counts.high++;
                  else if (sev === "MEDIUM") counts.medium++;
                  else if (sev === "LOW") counts.low++;
                  else counts.info++;
                }
                return counts;
              },
              renderCell: (value: unknown) => {
                const c = value as { high: number; medium: number; low: number; info: number };
                const total = c.high + c.medium + c.low + c.info;
                if (total === 0) {
                  return (
                    <span className="inline-flex items-center gap-1 text-xs text-green-600">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Clean
                    </span>
                  );
                }
                return (
                  <span className="inline-flex items-center gap-2 text-xs">
                    {c.high > 0 && (
                      <span className="inline-flex items-center gap-0.5 text-red-600 font-medium">
                        <ShieldAlert className="h-3.5 w-3.5" />
                        {c.high}
                      </span>
                    )}
                    {c.medium > 0 && (
                      <span className="inline-flex items-center gap-0.5 text-amber-600">
                        <AlertTriangle className="h-3.5 w-3.5" />
                        {c.medium}
                      </span>
                    )}
                    {(c.low + c.info) > 0 && (
                      <span className="text-gray-400">
                        +{c.low + c.info}
                      </span>
                    )}
                  </span>
                );
              },
            },
          ]}
        />
      </main>
    </div>
  );
}
