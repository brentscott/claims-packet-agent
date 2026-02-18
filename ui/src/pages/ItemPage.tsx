import { useEffect, useState, useMemo } from "react";
import {
  AcceptReject,
  ExtractedDataDisplay,
  FilePreview,
  useItemData,
  type Highlight,
  type ExtractedData,
  Button,
} from "@llamaindex/ui";
import {
  Clock,
  XCircle,
  Download,
  ChevronLeft,
  ChevronRight,
  FileText,
} from "lucide-react";
import { useParams } from "react-router-dom";
import { useToolbar } from "@/lib/ToolbarContext";
import { useNavigate } from "react-router-dom";
import { modifyJsonSchema } from "@llamaindex/ui/lib";
import { APP_TITLE } from "@/lib/config";
import { downloadExtractedDataItem } from "@/lib/export";
import { useMetadataContext } from "@/lib/MetadataProvider";
import { convertBoundingBoxesToHighlights } from "@/lib/utils";
import {
  PacketSummaryView,
  isClaimsPacket,
  type ClaimsPacketData,
} from "@/components/PacketSummaryView";
import { cn } from "@/lib/utils";

/**
 * Select the appropriate schema based on the discriminator field value.
 */
function selectSchemaForItem(
  metadata: {
    json_schema: any;
    schemas?: Record<string, any>;
    discriminator_field?: string;
  },
  itemData: any,
): any {
  const { schemas, discriminator_field, json_schema } = metadata;

  if (!schemas || !discriminator_field) {
    return json_schema;
  }

  const discriminatorValue = itemData?.data?.data?.[discriminator_field];

  if (discriminatorValue && schemas[discriminatorValue]) {
    return schemas[discriminatorValue];
  }

  return json_schema;
}

/**
 * Extract file_ids from packet documents for the file navigator.
 * Returns array of {file_id, filename, doc_type} for each document that has a file_id.
 */
function getPacketFileList(
  packetData: ClaimsPacketData,
): Array<{ file_id: string; filename: string; doc_type: string }> {
  return packetData.documents
    .filter((doc) => doc.envelope.file_id)
    .map((doc) => ({
      file_id: doc.envelope.file_id!,
      filename: doc.envelope.filename,
      doc_type: doc.envelope.classified_type,
    }));
}

/**
 * File navigator for multi-document packets.
 * Shows tabs/buttons for each file so users can page through all uploaded documents.
 */
function FileNavigator({
  files,
  activeIndex,
  onChange,
}: {
  files: Array<{ file_id: string; filename: string; doc_type: string }>;
  activeIndex: number;
  onChange: (index: number) => void;
}) {
  if (files.length <= 1) return null;

  return (
    <div className="border-b border-gray-200 bg-gray-50 px-2 py-2">
      <div className="flex items-center gap-1">
        <button
          onClick={() => onChange(Math.max(0, activeIndex - 1))}
          disabled={activeIndex === 0}
          className="p-1 rounded hover:bg-gray-200 disabled:opacity-30 disabled:cursor-not-allowed"
          aria-label="Previous document"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>

        <div className="flex-1 overflow-x-auto">
          <div className="flex gap-1">
            {files.map((file, i) => (
              <button
                key={file.file_id}
                onClick={() => onChange(i)}
                className={cn(
                  "flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs whitespace-nowrap transition-colors",
                  i === activeIndex
                    ? "bg-white shadow-sm border border-gray-200 text-gray-900 font-medium"
                    : "text-gray-600 hover:bg-gray-200 hover:text-gray-900",
                )}
                title={`${file.filename} (${file.doc_type})`}
              >
                <FileText className="h-3 w-3 shrink-0" />
                <span className="truncate max-w-[120px]">{file.filename}</span>
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={() =>
            onChange(Math.min(files.length - 1, activeIndex + 1))
          }
          disabled={activeIndex === files.length - 1}
          className="p-1 rounded hover:bg-gray-200 disabled:opacity-30 disabled:cursor-not-allowed"
          aria-label="Next document"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>

      <div className="text-center text-xs text-gray-400 mt-1">
        {activeIndex + 1} of {files.length} documents
      </div>
    </div>
  );
}

export default function ItemPage() {
  const { itemId } = useParams<{ itemId: string }>();
  const { setButtons, setBreadcrumbs } = useToolbar();
  const [highlight, setHighlight] = useState<Highlight | undefined>(undefined);
  const [activeFileIndex, setActiveFileIndex] = useState(0);
  const { metadata } = useMetadataContext();
  const navigate = useNavigate();

  const itemHookData = useItemData<any>({
    jsonSchema: modifyJsonSchema(metadata.json_schema, {}),
    itemId: itemId as string,
    isMock: false,
  });

  const selectedSchema = useMemo(() => {
    return selectSchemaForItem(metadata, itemHookData.item);
  }, [metadata, itemHookData.item]);

  const displaySchema = useMemo(() => {
    return modifyJsonSchema(selectedSchema, {});
  }, [selectedSchema]);

  // Detect if this is a claims packet or a single-document extraction
  const packetData = useMemo(() => {
    const innerData = itemHookData.item?.data?.data;
    if (isClaimsPacket(innerData)) {
      return innerData;
    }
    return null;
  }, [itemHookData.item]);

  // Get list of files available for preview in packet mode
  const packetFiles = useMemo(() => {
    if (!packetData) return [];
    return getPacketFileList(packetData);
  }, [packetData]);

  // Update breadcrumb when item data loads
  useEffect(() => {
    const extractedData = itemHookData.item?.data as
      | ExtractedData<unknown>
      | undefined;
    const fileName = extractedData?.file_name;
    if (fileName) {
      setBreadcrumbs([
        { label: APP_TITLE, href: "/" },
        {
          label: fileName,
          isCurrentPage: true,
        },
      ]);
    }

    return () => {
      setBreadcrumbs([{ label: APP_TITLE, href: "/" }]);
    };
  }, [itemHookData.item?.data, setBreadcrumbs]);

  const {
    item: itemData,
    updateData,
    loading: isLoading,
    error,
  } = itemHookData;

  useEffect(() => {
    setButtons(() => [
      <div className="ml-auto flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            if (itemData) {
              downloadExtractedDataItem(itemData);
            }
          }}
          disabled={!itemData}
          startIcon={<Download className="h-4 w-4" />}
          label="Export JSON"
        />
        <AcceptReject<any>
          itemData={itemHookData}
          onComplete={() => navigate("/")}
        />
      </div>,
    ]);
    return () => {
      setButtons(() => []);
    };
  }, [itemHookData.data, setButtons]);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <Clock className="h-8 w-8 animate-spin mx-auto mb-2" />
          <div className="text-sm text-gray-500">Loading item...</div>
        </div>
      </div>
    );
  }

  if (error || !itemData) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <XCircle className="h-8 w-8 text-red-500 mx-auto mb-2" />
          <div className="text-sm text-gray-500">
            Error loading item: {error || "Item not found"}
          </div>
        </div>
      </div>
    );
  }

  // --- Claims Packet View ---
  if (packetData) {
    // Determine which file to show in the preview
    const activeFileId =
      packetFiles.length > 0
        ? packetFiles[Math.min(activeFileIndex, packetFiles.length - 1)]
            ?.file_id
        : (itemData.data as ExtractedData<any>).file_id;

    return (
      <div className="flex h-full bg-gray-50">
        {/* Left Side - File Preview with Navigator */}
        <div className="w-2/5 border-r h-full border-gray-200 bg-white flex flex-col overflow-hidden">
          {/* File navigator tabs */}
          <FileNavigator
            files={packetFiles}
            activeIndex={Math.min(
              activeFileIndex,
              Math.max(0, packetFiles.length - 1),
            )}
            onChange={setActiveFileIndex}
          />

          {/* File preview */}
          <div className="flex-1 overflow-hidden">
            {activeFileId ? (
              <FilePreview
                key={activeFileId}
                fileId={activeFileId}
                onBoundingBoxClick={(box, pageNumber) => {
                  console.log(
                    "Bounding box clicked:",
                    box,
                    "on page:",
                    pageNumber,
                  );
                }}
                highlight={highlight}
              />
            ) : (
              <div className="flex items-center justify-center h-full text-gray-400 text-sm">
                No file preview available
              </div>
            )}
          </div>
        </div>

        {/* Right Side - Packet Summary */}
        <div className="flex-1 bg-gray-50 h-full overflow-y-auto">
          <PacketSummaryView data={packetData} />
        </div>
      </div>
    );
  }

  // --- Standard Single-Document View (fallback) ---
  const extractedData = itemData.data as ExtractedData<any>;
  const fileId = extractedData.file_id;

  return (
    <div className="flex h-full bg-gray-50">
      {/* Left Side - File Preview */}
      <div className="w-1/2 border-r h-full border-gray-200 bg-white">
        {fileId && (
          <FilePreview
            fileId={fileId}
            onBoundingBoxClick={(box, pageNumber) => {
              console.log(
                "Bounding box clicked:",
                box,
                "on page:",
                pageNumber,
              );
            }}
            highlight={highlight}
          />
        )}
      </div>

      {/* Right Side - Review Panel */}
      <div className="flex-1 bg-white h-full overflow-y-auto">
        <div className="p-4 space-y-4">
          <ExtractedDataDisplay<any>
            extractedData={extractedData}
            title="Extracted Data"
            onChange={(updatedData) => {
              updateData(updatedData);
            }}
            onHoverField={(args) => {
              const highlights = convertBoundingBoxesToHighlights(
                args?.metadata?.citation,
              );
              setHighlight(highlights[0]);
            }}
            jsonSchema={displaySchema}
          />
        </div>
      </div>
    </div>
  );
}
