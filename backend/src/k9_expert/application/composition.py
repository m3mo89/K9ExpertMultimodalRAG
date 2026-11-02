"""Dependency composition. Concrete adapters are added without leaking into domain code."""

from __future__ import annotations

import os
import tomllib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import httpx

from k9_expert.application.admin import AdminSecurityService
from k9_expert.application.agent import DomainPreservingReformulator
from k9_expert.application.breed_analysis import BreedAnalysisService, EvidenceBreedDiscovery
from k9_expert.application.breed_match import DeterministicBreedMatcher
from k9_expert.application.breed_profile import BreedProfileService
from k9_expert.application.breed_registry import BreedRegistry
from k9_expert.application.documents import DocumentRegistrationService, PdfValidator
from k9_expert.application.generation import (
    PROMPT_VERSION,
    OllamaTextGateway,
    RoutedOllamaGateway,
)
from k9_expert.application.guardrails import InputGuardrailChain
from k9_expert.application.indexing import SnapshotIndexBuilder, SnapshotRetriever
from k9_expert.application.ingestion import IngestionWorker
from k9_expert.application.interactions import InteractionService
from k9_expert.application.lifecycle import DocumentLifecycleService
from k9_expert.application.maintenance import (
    ComponentHealth,
    HealthService,
    OllamaModelProbe,
    OperationalMetricsService,
    ReindexService,
)
from k9_expert.application.observability import TelemetryService
from k9_expert.application.query import (
    EvidenceSufficiencyPolicy,
    QueryOrchestrator,
    SemanticRetriever,
)
from k9_expert.application.query_service import QueryService
from k9_expert.application.recovery import BackupService, IndexMaintainer, RestoreService
from k9_expert.application.response_cache import AnalysisResponseCache, QueryResponseCache
from k9_expert.application.routing import ComplexityRouter
from k9_expert.infrastructure.breed_images import PdfBreedImages
from k9_expert.infrastructure.embeddings import (
    CachingEmbedder,
    DocumentEmbedder,
    EmbeddingCache,
    OllamaEmbedder,
)
from k9_expert.infrastructure.extraction import TesseractOcrAdapter
from k9_expert.infrastructure.filesystem import ManagedFileStore
from k9_expert.infrastructure.sqlite import (
    BreedAnalysisRepository,
    CacheInvalidator,
    ContentRepository,
    DocumentRepository,
    InteractionRepository,
    JobRepository,
    SecurityRepository,
    SnapshotRepository,
    SqliteDatabase,
    SqliteResponseCache,
    SystemStateRepository,
    TraceRepository,
)
from k9_expert.ports.interfaces import Embedder


@dataclass(frozen=True, slots=True)
class ApplicationSettings:
    data_dir: Path = Path("data")
    host: str = "127.0.0.1"
    port: int = 8000
    worker_concurrency: int = 1
    admin_secret: str | None = None
    config_path: Path = Path("config/k9.defaults.toml")
    deleted_source_retention_days: int = 30
    retain_deleted_excerpts: bool = True
    text_model: str = "llama3.2:3b"
    embedding_model: str = "nomic-embed-text:latest"
    embedding_dimensions: int = 768
    embedding_query_prefix: str = "search_query: "
    embedding_document_prefix: str = "search_document: "
    retrieval_candidates: int = 24
    retrieval_top_k: int = 6
    retrieval_minimum_score: float = 0.0
    # Words, sized to fit the 8192-token generation context with the prompt.
    retrieval_context_tokens: int = 2500
    retrieval_max_per_section: int = 2
    sufficiency_minimum_score: float = 0.68
    generation_context_window: int = 8192
    allow_lan: bool = False
    trace_retention_days: int = 30
    feedback_comment_retention_days: int = 90
    # Privileged troubleshooting only: keeps full questions in stored traces.
    trace_store_protected: bool = False
    guardrail_policy_version: str = "guardrails-v1"
    exact_cache_ttl_seconds: int = 3600
    semantic_cache_ttl_seconds: int = 1800
    semantic_cache_threshold: float = 0.85
    agent_max_iterations: int = 2
    router_policy_version: str = "router-v1"
    text_simple_model: str = "llama3.2:3b"
    text_complex_model: str = "qwen3.5:2b"
    text_fallback_model: str = "llama3.2:3b"
    model_max_retries: int = 1
    model_timeout_seconds: int = 120
    breed_match_policy_version: str = "breed-match-v1"
    breed_match_minimum_coverage: float = 0.5
    breed_match_max_candidates: int = 5
    breed_match_discovery_pool: int = 20

    @property
    def files_dir(self) -> Path:
        return self.data_dir / "files"

    @property
    def index_dir(self) -> Path:
        return self.data_dir / "index"

    @property
    def backup_dir(self) -> Path:
        return self.data_dir / "backups"


@dataclass(frozen=True, slots=True)
class ApplicationContainer:
    settings: ApplicationSettings
    document_service: DocumentRegistrationService
    interaction_service: InteractionService
    query_service: QueryService
    admin_security: AdminSecurityService
    lifecycle_service: DocumentLifecycleService
    reindex_service: ReindexService
    health_service: HealthService
    metrics_service: OperationalMetricsService
    telemetry: TelemetryService
    backup_service: BackupService
    restore_service: RestoreService
    ingestion_worker: IngestionWorker
    system_state: SystemStateRepository
    breed_analysis_service: BreedAnalysisService
    breed_profile_service: BreedProfileService
    breed_registry: BreedRegistry


# TOML key -> settings field. The admin secret is deliberately not read from files.
_TOML_FIELDS = {
    ("server", "host"): "host",
    ("server", "port"): "port",
    ("server", "allow_lan"): "allow_lan",
    ("worker", "concurrency"): "worker_concurrency",
    ("models", "text_default_model"): "text_model",
    ("models", "embedding_default_model"): "embedding_model",
    ("models", "embedding_dimensions"): "embedding_dimensions",
    ("models", "embedding_query_prefix"): "embedding_query_prefix",
    ("models", "embedding_document_prefix"): "embedding_document_prefix",
    ("models", "generation_context_window"): "generation_context_window",
    ("retrieval", "candidates"): "retrieval_candidates",
    ("retrieval", "top_k"): "retrieval_top_k",
    ("retrieval", "minimum_similarity"): "retrieval_minimum_score",
    ("retrieval", "max_context_tokens"): "retrieval_context_tokens",
    ("retrieval", "max_per_section"): "retrieval_max_per_section",
    ("retrieval", "sufficiency_minimum_score"): "sufficiency_minimum_score",
    ("retention", "trace_days"): "trace_retention_days",
    ("retention", "feedback_comment_days"): "feedback_comment_retention_days",
    ("retention", "deleted_source_days"): "deleted_source_retention_days",
    ("telemetry", "store_protected"): "trace_store_protected",
    ("guardrails", "policy_version"): "guardrail_policy_version",
    ("cache", "exact_ttl_seconds"): "exact_cache_ttl_seconds",
    ("cache", "semantic_ttl_seconds"): "semantic_cache_ttl_seconds",
    ("cache", "semantic_threshold"): "semantic_cache_threshold",
    ("agent", "max_iterations"): "agent_max_iterations",
    ("router", "policy_version"): "router_policy_version",
    ("models", "text_simple_model"): "text_simple_model",
    ("models", "text_complex_model"): "text_complex_model",
    ("models", "text_fallback_model"): "text_fallback_model",
    ("models", "generation_max_retries"): "model_max_retries",
    ("models", "generation_timeout_seconds"): "model_timeout_seconds",
    ("breed_match", "policy_version"): "breed_match_policy_version",
    ("breed_match", "minimum_coverage"): "breed_match_minimum_coverage",
    ("breed_match", "max_candidates"): "breed_match_max_candidates",
    ("breed_match", "discovery_pool"): "breed_match_discovery_pool",
}


def load_settings(environ: Mapping[str, str] | None = None) -> ApplicationSettings:
    """Settings from the TOML file named by K9_CONFIG plus K9_DATA_DIR and K9_ADMIN_SECRET."""
    env = os.environ if environ is None else environ
    config_path = Path(env.get("K9_CONFIG", "config/k9.defaults.toml"))
    values: dict[str, object] = {}
    if config_path.is_file():
        raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
        for (section, key), field_name in _TOML_FIELDS.items():
            if key in raw.get(section, {}):
                values[field_name] = raw[section][key]
    return ApplicationSettings(
        data_dir=Path(env.get("K9_DATA_DIR", "data")),
        admin_secret=env.get("K9_ADMIN_SECRET") or None,
        config_path=config_path,
        **values,  # type: ignore[arg-type]
    )


def compose(
    settings: ApplicationSettings | None = None,
    model_probe: Callable[[], ComponentHealth] | None = None,
    embedder: Embedder | None = None,
) -> ApplicationContainer:
    """Build the production container; tests may substitute local-model adapters."""
    resolved = settings or load_settings()
    database = SqliteDatabase(resolved.data_dir / "k9.sqlite")
    database.migrate()
    file_store = ManagedFileStore(resolved.files_dir)
    documents = DocumentRepository(database)
    jobs = JobRepository(database)
    snapshots = SnapshotRepository(database)
    state = SystemStateRepository(database)
    service = DocumentRegistrationService(
        file_store,
        documents,
        jobs,
        PdfValidator(max_pages=1000),
        max_file_bytes=100 * 1024 * 1024,
    )
    interactions = InteractionRepository(database)
    admin_security = AdminSecurityService(SecurityRepository(database), resolved.admin_secret)
    # Embeddings: Ollama with task prefixes in production, a plain test double otherwise.
    ollama_embedder = OllamaEmbedder(
        model=resolved.embedding_model,
        query_prefix=resolved.embedding_query_prefix,
        document_prefix=resolved.embedding_document_prefix,
    )
    document_embedder: DocumentEmbedder = (
        ollama_embedder if embedder is None else _UnprefixedEmbedder(embedder)
    )
    cached_embedder = CachingEmbedder(
        document_embedder,
        EmbeddingCache(resolved.data_dir / "cache" / "embeddings"),
        resolved.embedding_dimensions,
    )
    # Snapshots record this identity; publishing under a different one needs a full reindex.
    embedding_identity = (
        document_embedder.alias,
        document_embedder.model,
        resolved.embedding_dimensions,
    )
    index_builder = SnapshotIndexBuilder(
        resolved.index_dir, cached_embedder.embed_documents, resolved.embedding_dimensions
    )
    response_cache_backend = SqliteResponseCache(database)
    cache_invalidator = CacheInvalidator(response_cache_backend)
    # Rebuilt vectors must use the same document prefix as ingestion.
    embed = embedder.embed if embedder else ollama_embedder.embed_documents
    index = IndexMaintainer(snapshots, resolved.index_dir, embed)
    lifecycle_service = DocumentLifecycleService(
        snapshots,
        cache_invalidator,
        documents,
        admin_security,
        retention_days=resolved.deleted_source_retention_days,
        file_store=file_store,
        retain_deleted_excerpts=resolved.retain_deleted_excerpts,
        prepare_index=index_builder,
        indexed_ids=index.indexed_ids,
    )
    traces = TraceRepository(database, store_protected=resolved.trace_store_protected)
    gateway = OllamaTextGateway(
        resolved.text_model, context_window=resolved.generation_context_window
    )
    selector = SemanticRetriever(
        top_k=resolved.retrieval_top_k,
        minimum_score=resolved.retrieval_minimum_score,
        context_tokens=resolved.retrieval_context_tokens,
        max_per_section=resolved.retrieval_max_per_section,
    )
    def embed_query(text: str) -> Sequence[float]:
        return (
            ollama_embedder.embed_queries([text])[0]
            if embedder is None
            else embedder.embed([text])[0]
        )

    retriever = SnapshotRetriever(
        resolved.index_dir,
        snapshots,
        embed_query,
        selector,
        candidates=resolved.retrieval_candidates,
    )
    # Upper layers only see the logical aliases; concrete local models stay in the gateway.
    routed_gateway = RoutedOllamaGateway(
        {
            alias: OllamaTextGateway(
                model,
                client=httpx.Client(
                    base_url="http://127.0.0.1:11434", timeout=resolved.model_timeout_seconds
                ),
                context_window=resolved.generation_context_window,
                # Structured answers: reasoning models (qwen) must not emit a thinking trace.
                think=False,
            )
            for alias, model in (
                ("simple", resolved.text_simple_model),
                ("complex", resolved.text_complex_model),
                ("fallback", resolved.text_fallback_model),
            )
        },
        "fallback",
        max_retries=resolved.model_max_retries,
    )
    query_service = QueryService(
        QueryOrchestrator(
            gateway.generate,
            retriever,
            sink=traces,
            text_alias=gateway.alias,
            resolved_model=lambda: gateway.resolved_model,
            sufficiency=EvidenceSufficiencyPolicy(resolved.sufficiency_minimum_score),
            response_cache=QueryResponseCache(
                response_cache_backend,
                embed_query,
                identity=(
                    f"query:{PROMPT_VERSION}:{resolved.guardrail_policy_version}:"
                    f"{resolved.router_policy_version}:{resolved.text_simple_model}:"
                    f"{resolved.text_complex_model}"
                ),
                exact_ttl_seconds=resolved.exact_cache_ttl_seconds,
                semantic_ttl_seconds=resolved.semantic_cache_ttl_seconds,
                semantic_threshold=resolved.semantic_cache_threshold,
            ),
            input_guardrails=InputGuardrailChain(),
            reformulate=DomainPreservingReformulator(),
            agent_max_iterations=resolved.agent_max_iterations,
            model_router=ComplexityRouter(resolved.router_policy_version),
            routed_gateway=routed_gateway,
            retrieval_config={
                "embedding_alias": ollama_embedder.alias,
                "embedding_model": resolved.embedding_model,
                "candidates": resolved.retrieval_candidates,
                "top_k": selector.top_k,
                "minimum_score": selector.minimum_score,
                "context_tokens": selector.context_tokens,
                "max_per_section": selector.max_per_section,
            },
        ),
        documents,
        interactions,
        state,
    )
    analysis_repository = BreedAnalysisRepository(database)
    telemetry = TelemetryService(
        traces,
        interactions,
        trace_retention_days=resolved.trace_retention_days,
        comment_retention_days=resolved.feedback_comment_retention_days,
        analyses=analysis_repository,
    )
    probe = model_probe or OllamaModelProbe(tuple(dict.fromkeys((
        resolved.text_simple_model,
        resolved.text_complex_model,
        resolved.text_fallback_model,
        resolved.embedding_model,
    ))))
    breed_registry = BreedRegistry(documents, snapshots)
    breed_analysis_service = BreedAnalysisService(
        documents,
        retriever,
        EvidenceBreedDiscovery(retriever.search, snapshots.fragment_breeds),
        analysis_repository,
        DeterministicBreedMatcher(resolved.breed_match_minimum_coverage),
        sink=traces,
        max_candidates=resolved.breed_match_max_candidates,
        cache=AnalysisResponseCache(
            response_cache_backend,
            embed_query,
            identity=(
                f"breed:{resolved.breed_match_policy_version}:"
                f"{resolved.guardrail_policy_version}:{resolved.router_policy_version}:"
                f"{resolved.text_simple_model}:{resolved.text_complex_model}"
            ),
            exact_ttl_seconds=resolved.exact_cache_ttl_seconds,
            semantic_ttl_seconds=resolved.semantic_cache_ttl_seconds,
            semantic_threshold=resolved.semantic_cache_threshold,
        ),
        router=ComplexityRouter(resolved.router_policy_version),
        gateway=routed_gateway,
        sufficiency=EvidenceSufficiencyPolicy(resolved.sufficiency_minimum_score),
        reformulate=DomainPreservingReformulator(),
        agent_max_iterations=resolved.agent_max_iterations,
        registry=breed_registry,
        discovery_pool=resolved.breed_match_discovery_pool,
    )
    return ApplicationContainer(
        settings=resolved,
        document_service=service,
        interaction_service=InteractionService(interactions),
        query_service=query_service,
        admin_security=admin_security,
        lifecycle_service=lifecycle_service,
        reindex_service=ReindexService(documents),
        health_service=HealthService(
            database,
            state,
            resolved.files_dir,
            resolved.index_dir,
            probe,
        ),
        metrics_service=OperationalMetricsService(database, telemetry, probe),
        telemetry=telemetry,
        backup_service=BackupService(
            database,
            resolved.files_dir,
            resolved.index_dir,
            resolved.backup_dir,
            resolved.config_path,
        ),
        restore_service=RestoreService(
            database,
            state,
            snapshots,
            index,
            resolved.files_dir,
            resolved.backup_dir,
            resolved.config_path,
        ),
        ingestion_worker=IngestionWorker(
            jobs,
            ContentRepository(database),
            sink=traces,
            embedding_config={
                "alias": ollama_embedder.alias,
                "model": resolved.embedding_model,
                "dimensions": resolved.embedding_dimensions,
                "normalized": True,
            },
            ocr=TesseractOcrAdapter(language="spa").extract_page,
            embed_fragments=cached_embedder.embed_documents,
            publish=lambda snapshot_id, version_id, fragment_ids, prepare: (
                snapshots.publish_version(
                    snapshot_id, version_id, fragment_ids, embedding_identity, prepare
                )
            ),
            prepare_index=index_builder,
            on_published=cache_invalidator.invalidate_snapshot,
            embedding_counter=lambda: (cached_embedder.hits, cached_embedder.misses),
            index_stats=lambda: {
                "vectors_reused_from_previous": index_builder.last_reused,
                "vectors_added": index_builder.last_embedded,
            },
        ),
        system_state=state,
        breed_analysis_service=breed_analysis_service,
        breed_profile_service=BreedProfileService(
            documents, snapshots, PdfBreedImages(resolved.data_dir / "cache" / "breed-images"),
            breed_registry,
        ),
        breed_registry=breed_registry,
    )


class _UnprefixedEmbedder:
    """Adapts a plain `Embedder` test double to the document-embedding contract."""

    def __init__(self, delegate: Embedder) -> None:
        self.delegate = delegate
        self.alias = delegate.alias
        self.model = f"test-double:{delegate.alias}"

    def embed_documents(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        return self.delegate.embed(texts)
