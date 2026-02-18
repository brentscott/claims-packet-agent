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
import { FileText } from "lucide-react";

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
            },
            status: true,
            createdAt: true,
            itemsToReview: {
              header: "Documents",
              getValue: (item: AgentDataItem) => {
                // Count documents in the packet from the nested data
                const packetData = (item.data as any)?.data;
                if (
                  packetData &&
                  Array.isArray(packetData.documents)
                ) {
                  return packetData.documents.length;
                }
                return 0;
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
        />
      </main>
    </div>
  );
}
