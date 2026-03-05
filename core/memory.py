"""
Base de conhecimento com ChromaDB.
Permite ao agente acessar informações de:
1. Consultas anteriores (transcrições e notas)
2. Artigos científicos e literatura médica (PDFs)
"""

import logging
import time
from typing import Optional, List, Dict
from pathlib import Path

logger = logging.getLogger(__name__)


class KnowledgeMemory:
    """
    Memória corporativa e científica baseada em embeddings vetoriais.
    """

    def __init__(self, config):
        self.config = config
        self._client = None
        self._collection = None
        self._is_initialized = False

    def initialize(self) -> bool:
        """Inicializa banco de dados ChromaDB."""
        try:
            import chromadb
            from chromadb.config import Settings

            persist_dir = Path(self.config.persist_directory)
            persist_dir.mkdir(parents=True, exist_ok=True)

            self._client = chromadb.PersistentClient(
                path=str(persist_dir),
                settings=Settings(anonymized_telemetry=False),
            )

            self._collection = self._client.get_or_create_collection(
                name=self.config.collection_name,
                metadata={"description": "Memória Clínica e Científica"},
            )

            self._is_initialized = True
            logger.info(f"✅ Base de conhecimento pronta ({self._collection.count()} docs)")
            return True

        except Exception as e:
            logger.error(f"❌ Erro ao inicializar ChromaDB: {e}")
            return False

    def add_consultation(
        self,
        transcription: str,
        patient_id: Optional[str] = None,
        diagnosis: Optional[str] = None,
        notes: Optional[str] = None,
        date: Optional[str] = None,
    ) -> bool:
        """Adiciona histórico de paciente na base de dados (memória clínica)."""
        if not self._is_initialized:
            return False

        try:
            doc_id = f"consultation_{int(time.time() * 1000)}"
            date_str = date or time.strftime("%Y-%m-%d")
            
            metadata = {
                "source_type": "consultation",
                "timestamp": time.time(),
                "date": date_str,
            }
            if patient_id: metadata["patient_id"] = patient_id
            if diagnosis: metadata["diagnosis"] = diagnosis

            # Monta o texto completo para virar "embbeding"
            full_text = f"Data da consulta: {date_str}\n" 
            if diagnosis: full_text += f"Diagnóstico: {diagnosis}\n"
            full_text += f"Transcrição da Consulta:\n{transcription}"
            if notes: full_text += f"\nNotas Médicas:\n{notes}"

            chunks = self._split_text(full_text, max_length=1500)
            
            ids = [f"{doc_id}_part_{i}" for i in range(len(chunks))]
            metadatas = [{**metadata, "chunk": i} for i in range(len(chunks))]

            self._collection.add(ids=ids, documents=chunks, metadatas=metadatas)
            logger.info(f"💾 Consulta indexada ({len(chunks)} blocos)")
            return True

        except Exception as e:
            logger.error(f"Erro ao adicionar consulta: {e}")
            return False

    def add_scientific_pdf(self, pdf_path: str, category: str = "article") -> bool:
        """
        Lê e indexa um artigo ou livro científico em PDF usando PyMuPDF (fitz).
        Sua IA vai usar isso pra responder duvidas embasadas!
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

            if not full_text.strip():
                logger.warning(f"O PDF {filename} não contém texto extraível.")
                return False

            chunks = self._split_text(full_text, max_length=1500)
            doc_id = f"article_{int(time.time())}_{filename.replace(' ', '_')}"
            
            ids = []
            documents = []
            metadatas = []
            
            for i, chunk in enumerate(chunks):
                ids.append(f"{doc_id}_{i}")
                documents.append(f"Fonte: {filename}\nTrecho:\n{chunk}")
                metadatas.append({
                    "source_type": "scientific_literature",
                    "filename": filename,
                    "category": category,
                    "chunk": i
                })

            # Adiciona ao banco vetorial
            self._collection.add(ids=ids, documents=documents, metadatas=metadatas)
            logger.info(f"🎓 Artigo indexado: {filename} ({len(chunks)} blocos aprendidos)")
            return True

        except ImportError:
            logger.error("❌ O pacote PyMuPDF (fitz) não está instalado. pip install PyMuPDF")
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
        Busca em AMBAS as bases (clínica e literatura) informações
        para fornecer o contexto definitivo para o Agente.
        """
        if not self._is_initialized:
            return {"consultations": [], "literature": []}

        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=n_results * 2, # Buscamos o dobro e filtramos
            )

            context = {
                "consultations": [],
                "literature": []
            }

            if results and results['documents'] and len(results['documents']) > 0:
                docs = results['documents'][0]
                metas = results['metadatas'][0]
                
                for doc, meta in zip(docs, metas):
                    src_type = meta.get("source_type", "")
                    
                    if src_type == "consultation" and len(context["consultations"]) < n_results:
                        context["consultations"].append(doc)
                    elif src_type == "scientific_literature" and len(context["literature"]) < n_results:
                        context["literature"].append(doc)

            return context

        except Exception as e:
            logger.error(f"Erro na busca mista: {e}")
            return {"consultations": [], "literature": []}

    def get_stats(self) -> Dict:
        if not self._is_initialized:
            return {"status": "offline"}

        try:
            return {"total_documents": self._collection.count()}
        except Exception:
            return {"status": "erro"}

    def _split_text(self, text: str, max_length: int = 1000) -> List[str]:
        """Divide textos longos (como artigos) em chunks por segurança semântica."""
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

    @property
    def is_initialized(self) -> bool:
        return self._is_initialized
