import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class MemoryEntry:
    content: str
    created_at: str


class MemoryStore:
    """Memoria persistente sobre SQLite + FTS5.

    Cada hecho se guarda como texto libre (sin estructura de sujeto/relación/
    objeto) — un modelo de 2-4B no genera de forma fiable sintaxis de grafo
    consistente, así que la búsqueda es full-text simple, no traversal.
    """

    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(db_path)
        self._connection.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS memory "
            "USING fts5(content, created_at UNINDEXED)"
        )
        self._connection.commit()

    def save(self, content: str) -> None:
        self._connection.execute(
            "INSERT INTO memory (content, created_at) VALUES (?, datetime('now'))",
            (content,),
        )
        self._connection.commit()

    def search(self, query: str, limit: int = 5) -> list[MemoryEntry]:
        rows = self._connection.execute(
            "SELECT content, created_at FROM memory "
            "WHERE memory MATCH ? ORDER BY rank, rowid DESC LIMIT ?",
            (_to_fts_query(query), limit),
        ).fetchall()
        return [MemoryEntry(content=row[0], created_at=row[1]) for row in rows]


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
