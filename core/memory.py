"""
Base de conhecimento com SQLite FTS5 (Full-Text Search).
Versão Lite: zero dependências externas, tudo embutido no Python.

Permite ao agente acessar informações de:
1. Consultas anteriores (transcrições e notas)
2. Artigos científicos e literatura médica (PDFs)
"""

import sqlite3
import logging
import time
from typing import Optional, List, Dict
from pathlib import Path

logger = logging.getLogger(__name__)


class KnowledgeMemory:
    """
    Memória clínica e científica baseada em SQLite FTS5.
    Busca textual full-text — leve, rápida, sem dependências.
    """

    def __init__(self, config):
        self.config = config
        self._db_path = config.db_path
        self._conn = None
        self._is_initialized = False

    def initialize(self) -> bool:
        """Inicializa banco de dados SQLite com FTS5."""
        try:
            db_dir = Path(self._db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)

            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row

            # Tabela principal de documentos
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    filename TEXT,
                    category TEXT,
                    patient_id TEXT,
                    diagnosis TEXT,
                    date TEXT,
                    chunk_index INTEGER DEFAULT 0,
                    created_at REAL
                )
            """)

            # Índice FTS5 para busca full-text rápida
            # tokenize='unicode61' lida bem com acentos do português
            self._conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                    content,
                    source_type,
                    filename,
                    diagnosis,
                    content_rowid='rowid',
                    tokenize='unicode61 remove_diacritics 2'
                )
            """)

            # Trigger para manter FTS sincronizado
            self._conn.execute("""
                CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents
                BEGIN
                    INSERT INTO documents_fts(rowid, content, source_type, filename, diagnosis)
                    VALUES (NEW.rowid, NEW.content, NEW.source_type, NEW.filename, NEW.diagnosis);
                END
            """)

            self._conn.execute("""
                CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents
                BEGIN
                    DELETE FROM documents_fts WHERE rowid = OLD.rowid;
                END
            """)

            self._conn.commit()
            self._is_initialized = True

            count = self._conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
            logger.info(f"✅ Base de conhecimento pronta ({count} docs) — SQLite FTS5")
            return True

        except Exception as e:
            logger.error(f"❌ Erro ao inicializar SQLite: {e}")
            return False

    def add_consultation(
        self,
        transcription: str,
        patient_id: Optional[str] = None,
        diagnosis: Optional[str] = None,
        notes: Optional[str] = None,
        date: Optional[str] = None,
    ) -> bool:
        """Adiciona histórico de paciente na base de dados."""
        if not self._is_initialized:
            return False

        try:
            doc_id = f"consultation_{int(time.time() * 1000)}"
            date_str = date or time.strftime("%Y-%m-%d")

            full_text = f"Data da consulta: {date_str}\n"
            if diagnosis:
                full_text += f"Diagnóstico: {diagnosis}\n"
            full_text += f"Transcrição da Consulta:\n{transcription}"
            if notes:
                full_text += f"\nNotas Médicas:\n{notes}"

            chunks = self._split_text(full_text, max_length=1500)

            for i, chunk in enumerate(chunks):
                self._conn.execute(
                    """INSERT INTO documents 
                       (id, content, source_type, patient_id, diagnosis, date, chunk_index, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (f"{doc_id}_part_{i}", chunk, "consultation",
                     patient_id, diagnosis, date_str, i, time.time())
                )

            self._conn.commit()
            logger.info(f"💾 Consulta indexada ({len(chunks)} blocos)")
            return True

        except Exception as e:
            logger.error(f"Erro ao adicionar consulta: {e}")
            return False

    def add_scientific_pdf(self, pdf_path: str, category: str = "article") -> bool:
        """
        Lê e indexa um artigo científico em PDF usando PyMuPDF.
        """
        if not self._is_initialized:
            return False

        try:
            import fitz  # PyMuPDF

            logger.info(f"📄 Lendo PDF científico: {pdf_path}")
            doc = fitz.open(pdf_path)
            full_text = ""
            filename = Path(pdf_path).name

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text("text").strip()
                if text:
                    full_text += f"\n[Página {page_num+1}]\n{text}"

            doc.close()

            if not full_text.strip():
                logger.warning(f"O PDF {filename} não contém texto extraível.")
                return False

            chunks = self._split_text(full_text, max_length=1500)
            doc_id = f"article_{int(time.time())}_{filename.replace(' ', '_')}"

            for i, chunk in enumerate(chunks):
                self._conn.execute(
                    """INSERT INTO documents 
                       (id, content, source_type, filename, category, chunk_index, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (f"{doc_id}_{i}", f"Fonte: {filename}\nTrecho:\n{chunk}",
                     "scientific_literature", filename, category, i, time.time())
                )

            self._conn.commit()
            logger.info(f"🎓 Artigo indexado: {filename} ({len(chunks)} blocos aprendidos)")
            return True

        except ImportError:
            logger.error("❌ PyMuPDF não instalado. pip install PyMuPDF")
            return False

        except Exception as e:
            logger.error(f"Erro ao processar PDF {pdf_path}: {e}")
            return False

    def search_for_context(
        self,
        query: str,
        n_results: int = 4
    ) -> Dict[str, List[str]]:
        """
        Busca em AMBAS bases (clínica + literatura) usando FTS5.
        Retorna contexto para o agente cruzar informações.
        """
        if not self._is_initialized:
            return {"consultations": [], "literature": []}

        try:
            # Preparar query para FTS5: adicionar * para busca parcial
            fts_query = " OR ".join(
                f'"{word}"*' for word in query.split() if len(word) > 2
            )

            if not fts_query:
                fts_query = f'"{query}"'

            results = self._conn.execute(
                """SELECT d.content, d.source_type 
                   FROM documents d
                   JOIN documents_fts fts ON d.rowid = fts.rowid
                   WHERE documents_fts MATCH ?
                   ORDER BY rank
                   LIMIT ?""",
                (fts_query, n_results * 2)
            ).fetchall()

            context = {
                "consultations": [],
                "literature": []
            }

            for row in results:
                content = row["content"]
                source_type = row["source_type"]

                if source_type == "consultation" and len(context["consultations"]) < n_results:
                    context["consultations"].append(content)
                elif source_type == "scientific_literature" and len(context["literature"]) < n_results:
                    context["literature"].append(content)

            return context

        except Exception as e:
            logger.error(f"Erro na busca: {e}")
            return {"consultations": [], "literature": []}

    def get_stats(self) -> Dict:
        """Retorna estatísticas do banco."""
        if not self._is_initialized:
            return {"status": "offline"}

        try:
            total = self._conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
            consultations = self._conn.execute(
                "SELECT COUNT(*) FROM documents WHERE source_type='consultation'"
            ).fetchone()[0]
            literature = self._conn.execute(
                "SELECT COUNT(*) FROM documents WHERE source_type='scientific_literature'"
            ).fetchone()[0]

            return {
                "total_documents": total,
                "consultations": consultations,
                "literature": literature,
                "engine": "SQLite FTS5"
            }
        except Exception:
            return {"status": "erro"}

    def _split_text(self, text: str, max_length: int = 1000) -> List[str]:
        """Divide textos longos em chunks por segurança semântica."""
        if len(text) <= max_length:
            return [text]

        chunks = []
        sentences = text.replace('\n', '. ').split('. ')
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 2 <= max_length:
                current_chunk += sentence + ". "
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks if chunks else [text[:max_length]]

    def close(self):
        """Fecha a conexão com o banco."""
        if self._conn:
            self._conn.close()
            self._conn = None

    @property
    def is_initialized(self) -> bool:
        return self._is_initialized
