"""
Agente LLM Médico com suporte avançado a RAG.
Consulta o histórico clínico e artigos científicos para embasar as respostas.
"""

import logging
import time
from typing import Optional, List, Dict, Generator
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Message:
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)


class MedicalAgent:
    def __init__(self, config, memory=None):
        self.config = config
        self.memory = memory
        self._client = None
        self._conversation: List[Message] = []
        self._is_available = False
        
        # O system prompt agora deve forçar a IA a se comportar como um especialista pesquisador
        sys_prompt =  (
            "Você é o IPagent, um assistente médico especialista em pesquisa clínica e apoio à decisão. "
            "Ao responder perguntas médicas, você será frequentemente munido de contexto extraído do histórico "
            "clínico (consultas do médico) e de literatura científica indexada (artigos/PDFs). \n\n"
            "DIRETRIZES FUNDAMENTAIS:\n"
            "1. Sempre priorize embasar suas respostas na LITERATURA CIENTÍFICA fornecida no contexto.\n"
            "2. Se informações do HISTÓRICO CLÍNICO forem fornecidas, cruze com o artigo científico para auxiliar.\n"
            "3. Caso fale sobre evidências do PDF anexado no contexto, cite que viu nos artigos.\n"
            "4. Nunca invente dados. Se a resposta não estiver no seu próprio conhecimento ou no contexto, diga que não sabe.\n"
            "5. A decisão final terapêutica é SEMPRE do médico humano. Redija em tom consultivo."
        )

        self._conversation.append(Message(role="system", content=sys_prompt))

    def initialize(self) -> bool:
        try:
            import ollama
            self._client = ollama.Client(host=self.config.ollama_host)
            
            # Forçar o modelo (Ex: mistral, qwen2.5, llama)
            # Dica: se for na VPS, pode usar um llm muito mais robusto
            self._client.chat(model=self.config.model_name, messages=[{"role": "user", "content": "olá"}])
            
            self._is_available = True
            logger.info(f"✅ Agente especialista inicializado")
            return True

        except Exception as e:
            logger.error(f"❌ Erro ao inicializar agente: {e}")
            return False

    def build_rag_prompt(self, user_message: str, current_consultation: Optional[str] = None) -> str:
        """Cria um super-prompt juntando Transcrição Ao Vivo + Memória + Artigos"""
        
        final_prompt = ""
        
        # 1. Obter contexto RAG (Artigos Científicos e Histórico Antigo)
        if self.memory and self.memory.is_initialized:
            contexts = self.memory.search_for_context(user_message, n_results=3)
            
            historico = contexts.get("consultations", [])
            literatura = contexts.get("literature", [])
            
            if historico or literatura:
                final_prompt += "=== CONTEXTO EXTRAÍDO DA NOSSA BASE DE DADOS ===\n\n"
                
                if literatura:
                    final_prompt += "[LITERATURA CIENTÍFICA ENCONTRADA]:\n"
                    for i, art in enumerate(literatura, 1):
                        final_prompt += f"--- Evidência {i} ---\n{art}\n\n"
                
                if historico:
                    final_prompt += "[CONSULTAS DO PASSADO]:\n"
                    for i, hist in enumerate(historico, 1):
                        final_prompt += f"--- Histórico {i} ---\n{hist}\n\n"
                        
        # 2. Contexto Ao Vivo (Se estivermos no meio de uma gravação agora)
        if current_consultation and len(current_consultation.strip()) > 10:
            final_prompt += f"=== CONTEXTAÇÃO AO VIVO DA CONSULTA ATUAL ===\n"
            final_prompt += f"{current_consultation}\n\n"
            
        # 3. A Pergunta de fato
        final_prompt += "=== A PERGUNTA / INSTRUÇÃO DO MÉDICO ===\n"
        final_prompt += user_message
        
        return final_prompt

    def chat(self, user_message: str, current_consultation: Optional[str] = None) -> str:
        if not self._is_available:
            return "⚠️ Agente indisponível."

        full_message = self.build_rag_prompt(user_message, current_consultation)

        self._conversation.append(Message(role="user", content=full_message))

        try:
            messages = [{"role": m.role, "content": m.content} for m in self._conversation[-10:]]

            response = self._client.chat(
                model=self.config.model_name,
                messages=messages,
                options={"temperature": 0.2, "num_ctx": 16000},
            )

            ast_resp = response.message.content
            self._conversation.append(Message(role="assistant", content=ast_resp))
            return ast_resp
        except Exception as e:
            return f"Erro: {e}"

    def chat_stream(self, user_message: str, current_consultation: Optional[str] = None) -> Generator[str, None, None]:
        if not self._is_available:
            yield "⚠️ Agente indisponível."
            return

        full_message = self.build_rag_prompt(user_message, current_consultation)
        self._conversation.append(Message(role="user", content=full_message))

        try:
            messages = [{"role": m.role, "content": m.content} for m in self._conversation[-10:]]

            stream = self._client.chat(
                model=self.config.model_name,
                messages=messages,
                options={"temperature": 0.2, "num_ctx": 16000}, # Contexto esticado p/ RAG
                stream=True,
            )

            full_response = ""
            for chunk in stream:
                token = chunk.message.content
                full_response += token
                yield token

            self._conversation.append(Message(role="assistant", content=full_response))
        except Exception as e:
            yield f"\n❌ Erro de processamento: {e}"
            
    def analyze_transcription(self, transcription: str) -> str:
        # Pede pra analisar e ver se temos na literatura cruzada
        return self.chat(
            "Estou fazendo esta consulta agora. Baseado no que o paciente falou, cruze com nossas diretrizes e sugira um plano."
        )

    def generate_soap_note(self, transcription: str) -> str:
        return self.chat(
            "Gere uma nota padrão SOAP baseada exclusivamente nesta consulta atual."
        )

    @property
    def is_available(self) -> bool:
        return self._is_available
