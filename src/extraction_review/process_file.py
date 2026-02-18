"""Insurance Claims Packet Agent workflow.

A 5-step pipeline that:
1. Parses documents using LlamaParse
2. Classifies documents into 7 types (EOB, CMS-1500, UB-04, etc.)
3. Extracts structured data using type-specific schemas
4. Validates across documents with 11 deterministic checks
5. Summarizes with financial reconciliation and action items
"""

import logging
import uuid
from typing import Annotated, Literal

from llama_cloud import AsyncLlamaCloud
from llama_cloud.types.classifier.classifier_rule_param import ClassifierRuleParam
from llama_cloud.types.extraction.extract_config_param import ExtractConfigParam
from llama_cloud.types.file_query_params import Filter
from llama_index.core.llms import LLM
from llama_index.core.prompts import PromptTemplate
from pydantic import BaseModel
from workflows import Context, Workflow, step
from workflows.events import Event, StartEvent, StopEvent
from workflows.resource import Resource, ResourceConfig

from .clients import agent_name, get_llama_cloud_client, project_id
from .config import (
    EXTRACTED_DATA_COLLECTION,
    ClassifyConfig,
    ExtractConfig,
    ParseConfig,
)
from .schemas import (
    ClaimsPacketOutput,
    DocumentEnvelope,
    DocumentType,
    FinancialSummary,
    PatientInfo,
    ProcessedDocument,
    ValidationResult,
    ValidationSeverity,
)
from .validators import run_all_validations

logger = logging.getLogger(__name__)


# --- LLM Provider ---


def get_llm() -> LLM:
    """LLM for generating patient-friendly summaries."""
    from llama_index.llms.openai import OpenAI

    return OpenAI(model="gpt-4o-mini", temperature=0)


# --- Events ---


class PacketStartEvent(StartEvent):
    """Start event with list of file IDs to process."""

    file_ids: list[str]


class StatusEvent(Event):
    """Progress status update for the client."""

    message: str
    level: Literal["info", "warning", "error"] = "info"


class DocumentsParsedEvent(Event):
    """Emitted after all documents are parsed."""

    pass


class DocumentsClassifiedEvent(Event):
    """Emitted after all documents are classified."""

    pass


class DocumentsExtractedEvent(Event):
    """Emitted after all documents have structured data extracted."""

    pass


class ValidationCompleteEvent(Event):
    """Emitted after cross-document validation is complete."""

    pass


# --- Workflow State ---


class ParsedDocument(BaseModel):
    """A document after parsing."""

    file_id: str
    filename: str
    markdown: str


class ClassifiedDocument(BaseModel):
    """A document after classification."""

    file_id: str
    filename: str
    markdown: str
    doc_type: str
    confidence: float


class WorkflowState(BaseModel):
    """State persisted across workflow steps."""

    packet_id: str = ""
    file_ids: list[str] = []
    parsed_docs: list[ParsedDocument] = []
    classified_docs: list[ClassifiedDocument] = []
    extracted_docs: list[ProcessedDocument] = []
    validation_results: list[ValidationResult] = []
    financial_summary: FinancialSummary | None = None


# --- Classification Rules ---

CLASSIFICATION_RULES = [
    ClassifierRuleParam(
        type="EOB",
        description="Explanation of Benefits from an insurance company showing how a claim was processed, including billed amounts, allowed amounts, insurance payments, and patient responsibility.",
    ),
    ClassifierRuleParam(
        type="CMS-1500",
        description="Professional claim form (CMS-1500/HCFA-1500) used by physicians and suppliers, with numbered boxes for patient, provider, diagnosis codes, and service lines.",
    ),
    ClassifierRuleParam(
        type="UB-04",
        description="Institutional claim form (UB-04/CMS-1450) used by hospitals and facilities, with revenue codes, condition codes, and occurrence codes.",
    ),
    ClassifierRuleParam(
        type="MEDICAL_BILL",
        description="Provider bill or patient statement showing charges, adjustments, payments, and balance due. May include account number and payment options.",
    ),
    ClassifierRuleParam(
        type="PHARMACY_RECEIPT",
        description="Pharmacy prescription receipt showing medication name, NDC code, quantity, days supply, and cost breakdown including copay.",
    ),
    ClassifierRuleParam(
        type="LAB_REPORT",
        description="Laboratory test results report showing test names, values, units, reference ranges, and flags for abnormal results.",
    ),
    ClassifierRuleParam(
        type="UNKNOWN",
        description="Document that does not match any of the above healthcare document types.",
    ),
]


# --- Prompts ---

SUMMARY_PROMPT = PromptTemplate(
    """You are an insurance claims analyst assistant. Given the extracted data
and validation results from a patient's insurance claims packet, write
a clear, actionable summary in plain English.

The patient is not an insurance expert. Use simple language. Focus on:
1. What happened (services received, from whom, when)
2. What they owe and why
3. Any problems found — overcharges, duplicate bills, denied services
4. Exactly what they should do next, in priority order

Be specific with dollar amounts, provider names, and deadlines. Do not
hedge or use vague language. If there's a $300 overcharge, say "You are
being overcharged $300" not "There may be a potential discrepancy."

EXTRACTED DOCUMENTS:
{documents_json}

VALIDATION RESULTS:
{validation_json}

FINANCIAL SUMMARY:
{financial_json}

Write a 2-4 paragraph summary. Start with the most important finding.
End with a numbered action list."""
)


# --- Workflow ---


class ClaimsPacketWorkflow(Workflow):
    """Analyze insurance claims packets to find billing errors and coverage gaps."""

    @step()
    async def parse_documents(
        self,
        event: PacketStartEvent,
        ctx: Context[WorkflowState],
        llama_cloud: Annotated[AsyncLlamaCloud, Resource(get_llama_cloud_client)],
        parse_config: Annotated[
            ParseConfig,
            ResourceConfig(
                config_file="configs/config.json",
                path_selector="parse",
                label="Parse Settings",
                description="Configuration for document parsing",
            ),
        ],
    ) -> DocumentsParsedEvent:
        """Parse uploaded documents to extract text content."""
        packet_id = str(uuid.uuid4())[:8]

        async with ctx.store.edit_state() as state:
            state.packet_id = packet_id
            state.file_ids = event.file_ids

        ctx.write_event_to_stream(
            StatusEvent(message=f"Processing {len(event.file_ids)} documents...")
        )

        parsed_docs: list[ParsedDocument] = []

        for file_id in event.file_ids:
            files = await llama_cloud.files.query(filter=Filter(file_ids=[file_id]))
            filename = files.items[0].name if files.items else file_id

            ctx.write_event_to_stream(StatusEvent(message=f"Parsing {filename}..."))

            parse_job = await llama_cloud.parsing.create(
                tier=parse_config.settings.tier,
                version=parse_config.settings.version,
                file_id=file_id,
            )

            await llama_cloud.parsing.wait_for_completion(parse_job.id)
            result = await llama_cloud.parsing.get(parse_job.id, expand=["markdown"])

            markdown_content = ""
            if result.markdown:
                for page in result.markdown.pages:
                    if hasattr(page, "markdown") and page.markdown:
                        markdown_content += page.markdown + "\n\n"

            parsed_docs.append(
                ParsedDocument(
                    file_id=file_id,
                    filename=filename,
                    markdown=markdown_content,
                )
            )

        async with ctx.store.edit_state() as state:
            state.parsed_docs = parsed_docs

        return DocumentsParsedEvent()

    @step()
    async def classify_documents(
        self,
        event: DocumentsParsedEvent,
        ctx: Context[WorkflowState],
        llama_cloud: Annotated[AsyncLlamaCloud, Resource(get_llama_cloud_client)],
        classify_config: Annotated[
            ClassifyConfig,
            ResourceConfig(
                config_file="configs/config.json",
                path_selector="classify",
                label="Classification Rules",
                description="Rules for classifying document types",
            ),
        ],
    ) -> DocumentsClassifiedEvent:
        """Classify each document into one of 7 healthcare document types."""
        state = await ctx.store.get_state()

        ctx.write_event_to_stream(StatusEvent(message="Classifying document types..."))

        rules = (
            [
                ClassifierRuleParam(type=r.type, description=r.description)
                for r in classify_config.rules
            ]
            if classify_config.rules
            else CLASSIFICATION_RULES
        )

        classified_docs: list[ClassifiedDocument] = []

        for doc in state.parsed_docs:
            classify_job = await llama_cloud.classifier.jobs.create(
                file_ids=[doc.file_id],
                rules=rules,
                mode=classify_config.settings.mode,
            )

            await llama_cloud.classifier.wait_for_completion(classify_job.id)
            result = await llama_cloud.classifier.jobs.get_results(classify_job.id)

            doc_type = "UNKNOWN"
            confidence = 0.0

            if result.items and result.items[0].result:
                doc_type = result.items[0].result.type
                confidence = result.items[0].result.confidence or 0.0

            classified_docs.append(
                ClassifiedDocument(
                    file_id=doc.file_id,
                    filename=doc.filename,
                    markdown=doc.markdown,
                    doc_type=doc_type,
                    confidence=confidence,
                )
            )

            ctx.write_event_to_stream(
                StatusEvent(
                    message=f"Classified {doc.filename} as {doc_type} ({confidence:.0%} confidence)"
                )
            )

        async with ctx.store.edit_state() as state:
            state.classified_docs = classified_docs

        return DocumentsClassifiedEvent()

    @step()
    async def extract_data(
        self,
        event: DocumentsClassifiedEvent,
        ctx: Context[WorkflowState],
        llama_cloud: Annotated[AsyncLlamaCloud, Resource(get_llama_cloud_client)],
        eob_config: Annotated[
            ExtractConfig,
            ResourceConfig(
                config_file="configs/config.json",
                path_selector="extract-eob",
                label="EOB Extraction",
                description="Schema for extracting Explanation of Benefits data",
            ),
        ],
        cms1500_config: Annotated[
            ExtractConfig,
            ResourceConfig(
                config_file="configs/config.json",
                path_selector="extract-cms1500",
                label="CMS-1500 Extraction",
                description="Schema for extracting CMS-1500 claim form data",
            ),
        ],
        ub04_config: Annotated[
            ExtractConfig,
            ResourceConfig(
                config_file="configs/config.json",
                path_selector="extract-ub04",
                label="UB-04 Extraction",
                description="Schema for extracting UB-04 institutional claim data",
            ),
        ],
        bill_config: Annotated[
            ExtractConfig,
            ResourceConfig(
                config_file="configs/config.json",
                path_selector="extract-medical-bill",
                label="Medical Bill Extraction",
                description="Schema for extracting medical bill data",
            ),
        ],
        pharmacy_config: Annotated[
            ExtractConfig,
            ResourceConfig(
                config_file="configs/config.json",
                path_selector="extract-pharmacy",
                label="Pharmacy Receipt Extraction",
                description="Schema for extracting pharmacy receipt data",
            ),
        ],
        lab_config: Annotated[
            ExtractConfig,
            ResourceConfig(
                config_file="configs/config.json",
                path_selector="extract-lab",
                label="Lab Report Extraction",
                description="Schema for extracting lab report data",
            ),
        ],
    ) -> DocumentsExtractedEvent:
        """Extract structured data from each document using type-specific schemas."""
        state = await ctx.store.get_state()

        config_map: dict[str, ExtractConfig] = {
            "EOB": eob_config,
            "CMS-1500": cms1500_config,
            "UB-04": ub04_config,
            "MEDICAL_BILL": bill_config,
            "PHARMACY_RECEIPT": pharmacy_config,
            "LAB_REPORT": lab_config,
        }

        extracted_docs: list[ProcessedDocument] = []

        for i, doc in enumerate(state.classified_docs):
            ctx.write_event_to_stream(
                StatusEvent(message=f"Extracting data from {doc.filename}...")
            )

            doc_id = f"{state.packet_id}-{i}"
            config = config_map.get(doc.doc_type)

            if not config:
                extracted_docs.append(
                    ProcessedDocument(
                        envelope=DocumentEnvelope(
                            doc_id=doc_id,
                            file_id=doc.file_id,
                            filename=doc.filename,
                            classified_type=DocumentType.UNKNOWN,
                            classification_confidence=doc.confidence,
                            extraction_warnings=[
                                "No schema available for document type"
                            ],
                        ),
                        extracted_data={},
                        schema_used=DocumentType.UNKNOWN,
                    )
                )
                continue

            extract_job = await llama_cloud.extraction.run(
                config=ExtractConfigParam(
                    extraction_mode=config.settings.extraction_mode,
                    system_prompt=config.settings.system_prompt,
                    citation_bbox=config.settings.citation_bbox,
                    use_reasoning=config.settings.use_reasoning,
                    cite_sources=config.settings.cite_sources,
                    confidence_scores=config.settings.confidence_scores,
                ),
                data_schema=config.json_schema,
                file_id=doc.file_id,
                project_id=project_id,
            )

            await llama_cloud.extraction.jobs.wait_for_completion(extract_job.id)
            result = await llama_cloud.extraction.jobs.get_result(extract_job.id)

            doc_type_enum = DocumentType.UNKNOWN
            for dt in DocumentType:
                if dt.value == doc.doc_type:
                    doc_type_enum = dt
                    break

            extracted_docs.append(
                ProcessedDocument(
                    envelope=DocumentEnvelope(
                        doc_id=doc_id,
                        file_id=doc.file_id,
                        filename=doc.filename,
                        classified_type=doc_type_enum,
                        classification_confidence=doc.confidence,
                    ),
                    extracted_data=result.data or {},
                    schema_used=doc_type_enum,
                )
            )

        async with ctx.store.edit_state() as state:
            state.extracted_docs = extracted_docs

        return DocumentsExtractedEvent()

    @step()
    async def validate_documents(
        self,
        event: DocumentsExtractedEvent,
        ctx: Context[WorkflowState],
    ) -> ValidationCompleteEvent:
        """Run 11 cross-document validation checks to find billing errors."""
        state = await ctx.store.get_state()

        ctx.write_event_to_stream(StatusEvent(message="Running validation checks..."))

        validation_results = run_all_validations(state.extracted_docs)
        financial_summary = _compute_financial_summary(
            state.extracted_docs, validation_results
        )

        async with ctx.store.edit_state() as state:
            state.validation_results = validation_results
            state.financial_summary = financial_summary

        high_issues = sum(
            1 for r in validation_results if r.severity == ValidationSeverity.HIGH
        )
        medium_issues = sum(
            1 for r in validation_results if r.severity == ValidationSeverity.MEDIUM
        )

        if high_issues > 0 or medium_issues > 0:
            ctx.write_event_to_stream(
                StatusEvent(
                    message=f"Found {high_issues} critical and {medium_issues} important issues",
                    level="warning",
                )
            )
        else:
            ctx.write_event_to_stream(
                StatusEvent(message="All validation checks passed")
            )

        return ValidationCompleteEvent()

    @step()
    async def summarize(
        self,
        event: ValidationCompleteEvent,
        ctx: Context[WorkflowState],
        llama_cloud: Annotated[AsyncLlamaCloud, Resource(get_llama_cloud_client)],
        llm: Annotated[LLM, Resource(get_llm)],
    ) -> StopEvent:
        """Generate financial summary, action list, and plain-English narrative."""
        state = await ctx.store.get_state()

        ctx.write_event_to_stream(StatusEvent(message="Generating summary..."))

        patient = _consolidate_patient(state.extracted_docs)
        actions = _build_action_list(state.validation_results)

        documents_json = [
            {
                "type": d.envelope.classified_type.value,
                "filename": d.envelope.filename,
                "data": d.extracted_data,
            }
            for d in state.extracted_docs
        ]

        validation_json = [r.model_dump() for r in state.validation_results]
        financial_json = (
            state.financial_summary.model_dump() if state.financial_summary else {}
        )

        narrative = await llm.acomplete(
            SUMMARY_PROMPT.format(
                documents_json=documents_json,
                validation_json=validation_json,
                financial_json=financial_json,
            )
        )

        output = ClaimsPacketOutput(
            packet_id=state.packet_id,
            patient=patient,
            documents=state.extracted_docs,
            validation_results=state.validation_results,
            financial_summary=state.financial_summary or FinancialSummary(),
            recommended_actions=actions,
            summary_narrative=str(narrative),
        )

        output_dict = output.model_dump(mode="json")

        # Get filenames for display
        filenames = [doc.envelope.filename for doc in state.extracted_docs]
        display_name = (
            filenames[0] if len(filenames) == 1 else f"{state.packet_id} ({len(filenames)} files)"
        )

        # Wrap output in the format expected by the UI
        wrapped_output = {
            "data": output_dict,
            "file_name": display_name,
            "file_id": state.file_ids[0] if state.file_ids else None,
            "status": "pending_review",
        }

        await llama_cloud.beta.agent_data.agent_data(
            data=wrapped_output,
            deployment_name=agent_name or "_public",
            collection=EXTRACTED_DATA_COLLECTION,
        )

        ctx.write_event_to_stream(StatusEvent(message="Analysis complete"))

        return StopEvent(result=output_dict)


# --- Helper Functions ---


def _compute_financial_summary(
    documents: list[ProcessedDocument],
    validation_results: list[ValidationResult],
) -> FinancialSummary:
    """Aggregate financial information across all documents."""
    total_billed = 0.0
    total_allowed = 0.0
    total_insurance_paid = 0.0
    eob_patient_resp = 0.0
    bill_patient_resp = 0.0

    for doc in documents:
        data = doc.extracted_data
        doc_type = doc.envelope.classified_type.value

        if doc_type == "EOB":
            if data.get("total_billed"):
                total_billed += data["total_billed"]
            if data.get("total_allowed"):
                total_allowed += data["total_allowed"]
            if data.get("total_insurance_paid"):
                total_insurance_paid += data["total_insurance_paid"]
            if data.get("total_patient_responsibility"):
                eob_patient_resp += data["total_patient_responsibility"]

        elif doc_type == "MEDICAL_BILL":
            if data.get("balance_due"):
                bill_patient_resp += data["balance_due"]

    discrepancy = bill_patient_resp - eob_patient_resp if eob_patient_resp > 0 else None
    potential_savings = sum(r.potential_overcharge or 0 for r in validation_results)
    flagged_issues = sum(
        1
        for r in validation_results
        if r.severity in (ValidationSeverity.HIGH, ValidationSeverity.MEDIUM)
    )

    return FinancialSummary(
        total_billed=total_billed or None,
        total_allowed=total_allowed or None,
        total_insurance_paid=total_insurance_paid or None,
        total_patient_responsibility_per_eob=eob_patient_resp or None,
        total_patient_responsibility_per_bills=bill_patient_resp or None,
        discrepancy_amount=discrepancy,
        potential_savings=potential_savings or None,
        flagged_issues=flagged_issues,
    )


def _consolidate_patient(documents: list[ProcessedDocument]) -> PatientInfo:
    """Extract best patient info from all documents."""
    patient = PatientInfo()

    for doc in documents:
        data = doc.extracted_data
        patient_data = data.get("patient", {})

        if not patient.first_name and patient_data.get("first_name"):
            patient.first_name = patient_data["first_name"]
        if not patient.last_name and patient_data.get("last_name"):
            patient.last_name = patient_data["last_name"]
        if not patient.date_of_birth and patient_data.get("date_of_birth"):
            patient.date_of_birth = patient_data["date_of_birth"]
        if not patient.member_id and patient_data.get("member_id"):
            patient.member_id = patient_data["member_id"]
        if not patient.group_number and patient_data.get("group_number"):
            patient.group_number = patient_data["group_number"]
        if not patient.address and patient_data.get("address"):
            patient.address = patient_data["address"]

    return patient


def _build_action_list(validation_results: list[ValidationResult]) -> list[str]:
    """Build prioritized action list from validation findings."""
    actions: list[str] = []

    for result in validation_results:
        if result.severity == ValidationSeverity.HIGH and result.recommendation:
            actions.append(f"URGENT: {result.recommendation}")
        elif result.severity == ValidationSeverity.MEDIUM and result.recommendation:
            actions.append(f"INVESTIGATE: {result.recommendation}")

    return actions


workflow = ClaimsPacketWorkflow(timeout=None)
