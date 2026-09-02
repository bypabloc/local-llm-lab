import logging
import sqlite3
import struct
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

EmbedFn = Callable[[str], list[float]]


@dataclass(frozen=True, slots=True)
class MemoryEntry:
    content: str
    created_at: str


def _normalize(content: str) -> str:
    return " ".join(content.lower().split())


def _pack_embedding(vector: list[float]) -> bytes:
    return struct.pack(f"<{len(vector)}f", *vector)


def _unpack_embedding(blob: bytes) -> list[float]:
    count = len(blob) // 4
    return list(struct.unpack(f"<{count}f", blob))


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


# ponytail: umbral calibrado con Qwen3-Embedding-0.6B real (no una
# suposición) — "¿sabes mi nombre?" vs "el usuario se llama Pablo" da 0.43,
# preguntas no relacionadas dan ~0.26-0.28. 0.35 separa ambos casos con
# margen. Recalibrar si se cambia el modelo de embeddings.
_SIMILARITY_THRESHOLD = 0.35


class MemoryStore:
    """Memoria persistente sobre SQLite + FTS5, con recall semántico opcional.

    Cada hecho se guarda como texto libre (sin estructura de sujeto/relación/
    objeto) — un modelo de 2-4B no genera de forma fiable sintaxis de grafo
    consistente, así que la búsqueda base es full-text simple, no traversal.
    Si se provee `embed_fn`, se complementa con búsqueda por similitud
    coseno sobre embeddings — cubre paráfrasis/sinónimos que el matching
    léxico por prefijo no puede alcanzar (ej. "nombre" vs "llama").
    """

    def __init__(self, db_path: Path, embed_fn: EmbedFn | None = None) -> None:
        self._embed_fn = embed_fn
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(db_path)
        self._connection.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS memory "
            "USING fts5(content, created_at UNINDEXED)"
        )
        # ponytail: FTS5 no soporta UNIQUE — tabla normal aparte solo para
        # deduplicar por contenido normalizado antes de insertar en memory.
        self._connection.execute(
            "CREATE TABLE IF NOT EXISTS memory_dedup (normalized TEXT PRIMARY KEY)"
        )
        self._connection.execute(
            "CREATE TABLE IF NOT EXISTS memory_embedding ("
            "content TEXT PRIMARY KEY, vector BLOB NOT NULL)"
        )
        self._connection.commit()

    def save(self, content: str) -> None:
        normalized = _normalize(content)
        exists = self._connection.execute(
            "SELECT 1 FROM memory_dedup WHERE normalized = ?", (normalized,)
        ).fetchone()
        if exists:
            logger.info("MemoryStore.save: contenido duplicado, omitido: %r", content)
            return

        self._connection.execute(
            "INSERT INTO memory (content, created_at) VALUES (?, datetime('now'))",
            (content,),
        )
        self._connection.execute(
            "INSERT INTO memory_dedup (normalized) VALUES (?)", (normalized,)
        )
        if self._embed_fn is not None:
            vector = self._embed_fn(content)
            self._connection.execute(
                "INSERT INTO memory_embedding (content, vector) VALUES (?, ?)",
                (content, _pack_embedding(vector)),
            )
            logger.info(
                "MemoryStore.save: guardado con embedding (%d dims): %r",
                len(vector),
                content,
            )
        else:
            logger.info("MemoryStore.save: guardado (sin embedding): %r", content)
        self._connection.commit()

    def search(self, query: str, limit: int = 5) -> list[MemoryEntry]:
        lexical = self._connection.execute(
            "SELECT content, created_at FROM memory "
            "WHERE memory MATCH ? ORDER BY rank, rowid DESC LIMIT ?",
            (_to_fts_query(query), limit),
        ).fetchall()
        logger.debug(
            "MemoryStore.search: búsqueda léxica de %r -> %d resultados",
            query,
            len(lexical),
        )
        results = {
            row[0]: MemoryEntry(content=row[0], created_at=row[1]) for row in lexical
        }

        if self._embed_fn is not None and len(results) < limit:
            semantic = self._semantic_search(
                query, limit - len(results), exclude=results.keys()
            )
            logger.debug(
                "MemoryStore.search: búsqueda semántica de %r -> %d adicionales",
                query,
                len(semantic),
            )
            for entry in semantic:
                results[entry.content] = entry

        final = list(results.values())[:limit]
        logger.info(
            "MemoryStore.search: %r -> %d resultado(s) final(es)", query, len(final)
        )
        return final

    def backfill_embeddings(self) -> int:
        """Genera el embedding faltante de hechos guardados antes de que
        `embed_fn` estuviera disponible (modelo no descargado aún, o
        guardados con una versión previa sin soporte semántico). Sin esto,
        esos hechos quedan invisibles al recall semántico para siempre,
        aunque el modelo de embeddings se active después."""
        if self._embed_fn is None:
            return 0
        rows = self._connection.execute(
            "SELECT content FROM memory "
            "WHERE content NOT IN (SELECT content FROM memory_embedding)"
        ).fetchall()
        for (content,) in rows:
            vector = self._embed_fn(content)
            self._connection.execute(
                "INSERT INTO memory_embedding (content, vector) VALUES (?, ?)",
                (content, _pack_embedding(vector)),
            )
        if rows:
            self._connection.commit()
            logger.info(
                "MemoryStore.backfill_embeddings: %d hecho(s) completados", len(rows)
            )
        return len(rows)

    def _semantic_search(
        self, query: str, limit: int, exclude: Iterable[str]
    ) -> list[MemoryEntry]:
        if self._embed_fn is None:
            return []
        query_vector = self._embed_fn(query)
        rows = self._connection.execute(
            "SELECT m.content, m.created_at, e.vector FROM memory m "
            "JOIN memory_embedding e ON e.content = m.content"
        ).fetchall()
        scored = [
            (
                content,
                created_at,
                _cosine_similarity(query_vector, _unpack_embedding(blob)),
            )
            for content, created_at, blob in rows
            if content not in exclude
        ]
        scored.sort(key=lambda row: row[2], reverse=True)
        return [
            MemoryEntry(content=content, created_at=created_at)
            for content, created_at, score in scored[:limit]
            if score >= _SIMILARITY_THRESHOLD
        ]


# ponytail: lista fija de stopwords en vez de una librería de NLP — el
# vocabulario de preguntas cortas en español es acotado y esto cubre los
# casos reales sin agregar una dependencia nueva al proyecto.
_STOPWORDS = {
    "a", "al", "como", "cual", "cuales", "cuando", "de", "del", "el", "en",
    "es", "esta", "este", "la", "las", "lo", "los", "me", "mi", "mis", "por",
    "que", "se", "su", "sus", "te", "tu", "tus", "un", "una", "y",
}  # fmt: skip


# ponytail: truncar a un prefijo fijo en vez de un stemmer real — cubre
# variaciones de conjugación simples en español ("llamo"/"llama"/"llamas")
# sin agregar una dependencia de NLP al proyecto.
_PREFIX_LENGTH = 4


def _to_fts_query(query: str) -> str:
    """Arma una búsqueda OR por prefijo entre las palabras relevantes de `query`.

    AND estricto falla en el caso real: una pregunta del usuario ("¿cómo me
    llamo?") rara vez comparte vocabulario literal con el hecho guardado
    ("el usuario se llama Pablo"). Se usa OR para maximizar recall, con
    matching por prefijo para tolerar variaciones de conjugación, filtrando
    antes las stopwords para no traer resultados por una sola palabra común
    (ej. "en" matcheando cualquier documento en español).
    """
    words = [w.strip('"') for w in query.lower().split()]
    relevant = [w for w in words if w and w not in _STOPWORDS]
    escaped = [w.replace('"', '""') for w in (relevant or words)]
    prefixed = [w[:_PREFIX_LENGTH] if len(w) > _PREFIX_LENGTH else w for w in escaped]
    return " OR ".join(f'"{w}"*' for w in prefixed) if prefixed else '""'
