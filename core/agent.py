"""
Agente LLM Médico — IPagent Ultra-Lite.
Roda LLM direto no Python via llama-cpp-python (sem Ollama).
Inclui correção médica de transcrição em 2 camadas.
"""

import logging
import time
import re
from typing import Optional, List, Dict, Generator
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Message:
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)


SYSTEM_PROMPT = (
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


class MedicalAgent:
    def __init__(self, config, model_manager=None, memory=None, correction_config=None):
        self.config = config
        self.model_manager = model_manager
        self.memory = memory
        self.correction_config = correction_config
        self._llm = None
        self._conversation: List[Message] = []
        self._is_available = False

        self._conversation.append(Message(role="system", content=SYSTEM_PROMPT))

    def initialize(self) -> bool:
        """Carrega o modelo LLM na memória."""
        try:
            if not self.model_manager:
                logger.error("❌ ModelManager não configurado")
                return False

            # Carrega modelo (baixa automaticamente se necessário)
            self._llm = self.model_manager.load(
                n_gpu_layers=self.config.n_gpu_layers,
                n_ctx=self.config.n_ctx,
            )

            # Teste rápido
            logger.info("🧪 Testando modelo...")
            test = self._llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": "Responda em 1 palavra."},
                    {"role": "user", "content": "Olá"}
                ],
                max_tokens=10,
                temperature=0.0,
            )
            test_response = test["choices"][0]["message"]["content"]
            logger.info(f"🧪 Resposta do teste: {test_response}")

            self._is_available = True
            logger.info(f"✅ Agente médico pronto! Modelo: {self.config.model_name}")
            return True

        except Exception as e:
            logger.error(f"❌ Erro ao inicializar agente: {e}")
            return False

    # ==========================================
    # CAMADA DE CORREÇÃO MÉDICA DA TRANSCRIÇÃO
    # ==========================================

    def quick_correct(self, text: str) -> str:
        """Camada 1: Correção instantânea via dicionário."""
        if not self.correction_config or not self.correction_config.quick_corrections:
            return text

        corrected = text
        for wrong, right in self.correction_config.quick_corrections.items():
            pattern = re.compile(re.escape(wrong), re.IGNORECASE)
            corrected = pattern.sub(right, corrected)

        return corrected

    def correct_transcription(self, raw_text: str) -> Dict[str, str]:
        """
        Camada 2: Correção profunda via LLM.
        Usa o modelo que JÁ está carregado.
        """
        if not self._is_available:
            return {"original": raw_text, "corrected": raw_text, "terms_found": ""}

        # Camada 1: Quick fix
        quick_fixed = self.quick_correct(raw_text)

        # Se texto curto, só retorna o quick fix
        min_words = 3
        if self.correction_config:
            min_words = self.correction_config.min_words_to_correct

        if len(quick_fixed.split()) < min_words:
            return {"original": raw_text, "corrected": quick_fixed, "terms_found": ""}

        # Camada 2: Correção por LLM
        try:
            response = self._llm.create_chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Você é um corretor ortográfico médico. "
                            "Sua ÚNICA função é receber um texto e devolver o texto corrigido. "
                            "REGRAS ABSOLUTAS:\n"
                            "- Corrija APENAS erros de ortografia e termos médicos errados\n"
                            "- Se o texto não tiver erros, repita-o exatamente igual\n"
                            "- NUNCA explique, comente ou recuse. APENAS devolva o texto\n"
                            "- Mantenha o idioma original (português)\n"
                            "- Formate nomes de medicamentos corretamente"
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Corrija: {quick_fixed}"
                    }
                ],
                max_tokens=max(len(quick_fixed) * 2, 200),
                temperature=0.1,
            )

            corrected = response["choices"][0]["message"]["content"].strip()

            # Remove aspas extras
            if corrected.startswith('"') and corrected.endswith('"'):
                corrected = corrected[1:-1]
            
            # Se o modelo adicionou explicação, descartar (pegar só a 1ª linha)
            if len(corrected) > len(quick_fixed) * 3:
                corrected = quick_fixed

            # Identifica termos médicos
            terms_prompt = (
                "Liste APENAS os termos médicos neste texto, separados por vírgula. "
                "Se não houver, responda 'nenhum'.\n"
                f'Texto: "{corrected}"\nTermos:'
            )

            terms_response = self._llm.create_chat_completion(
                messages=[{"role": "user", "content": terms_prompt}],
                max_tokens=200,
                temperature=0.0,
            )

            return {
                "original": raw_text,
                "corrected": corrected,
                "terms_found": terms_response["choices"][0]["message"]["content"].strip()
            }

        except Exception as e:
            logger.error(f"Erro na correção: {e}")
            return {"original": raw_text, "corrected": quick_fixed, "terms_found": ""}

    # ==========================================
    # RAG + CHAT
    # ==========================================

    def build_rag_prompt(self, user_message: str, current_consultation: Optional[str] = None) -> str:
        """Cria prompt juntando Transcrição + Memória + Artigos."""
        final_prompt = ""

        if self.memory and self.memory.is_initialized:
            contexts = self.memory.search_for_context(user_message, n_results=3)

            historico = contexts.get("consultations", [])
            literatura = contexts.get("literature", [])

            if historico or literatura:
                final_prompt += "=== CONTEXTO DA BASE DE DADOS ===\n\n"

                if literatura:
                    final_prompt += "[LITERATURA CIENTÍFICA]:\n"
                    for i, art in enumerate(literatura, 1):
                        final_prompt += f"--- Evidência {i} ---\n{art}\n\n"

                if historico:
                    final_prompt += "[CONSULTAS ANTERIORES]:\n"
                    for i, hist in enumerate(historico, 1):
                        final_prompt += f"--- Histórico {i} ---\n{hist}\n\n"

        if current_consultation and len(current_consultation.strip()) > 10:
            final_prompt += f"=== TRANSCRIÇÃO DA CONSULTA ATUAL ===\n{current_consultation}\n\n"

        final_prompt += "=== PERGUNTA DO MÉDICO ===\n"
        final_prompt += user_message

        return final_prompt

    def chat(self, user_message: str, context: Optional[str] = None) -> str:
        """Chat síncrono com o agente."""
        if not self._is_available:
            return "⚠️ Agente indisponível. Verifique se o modelo foi carregado."

        full_message = self.build_rag_prompt(user_message, context)
        self._conversation.append(Message(role="user", content=full_message))

        try:
            messages = [{"role": m.role, "content": m.content} for m in self._conversation[-10:]]

            response = self._llm.create_chat_completion(
                messages=messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            )

            ast_resp = response["choices"][0]["message"]["content"]
            self._conversation.append(Message(role="assistant", content=ast_resp))
            return ast_resp

        except Exception as e:
            return f"Erro: {e}"

    def chat_stream(self, user_message: str, context: Optional[str] = None) -> Generator[str, None, None]:
        """Chat com streaming — retorna tokens um a um."""
        if not self._is_available:
            yield "⚠️ Agente indisponível."
            return

        full_message = self.build_rag_prompt(user_message, context)
        self._conversation.append(Message(role="user", content=full_message))

        try:
            messages = [{"role": m.role, "content": m.content} for m in self._conversation[-10:]]

            stream = self._llm.create_chat_completion(
                messages=messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                stream=True,
            )

            full_response = ""
            for chunk in stream:
                delta = chunk["choices"][0].get("delta", {})
                token = delta.get("content", "")
                if token:
                    full_response += token
                    yield token

            self._conversation.append(Message(role="assistant", content=full_response))

        except Exception as e:
            yield f"\n❌ Erro: {e}"

    def analyze_transcription(self, transcription: str) -> str:
        return self.chat(
            "Analise esta consulta. Cruze com as diretrizes e sugira um plano.",
            context=transcription
        )

    def generate_soap_note(self, transcription: str) -> str:
        return self.chat(
            "Gere uma nota SOAP baseada exclusivamente nesta consulta.",
            context=transcription
        )

    # ==========================================
    # GERAÇÃO DE ANAMNESE EM TEMPO REAL
    # ==========================================

    DEFAULT_ANAMNESIS_PROMPT = (
        "Você é um assistente médico especializado em documentação clínica. "
        "Analise a transcrição da consulta e preencha o prontuário abaixo. "
        "Use APENAS informações que foram mencionadas na transcrição. "
        "Se algo não foi dito, escreva 'não informado'. "
        "Se receber uma anamnese anterior, ATUALIZE com as novas informações, "
        "mantendo o que já estava correto.\n\n"
        "---\n"
        "[NOME DO PACIENTE]\n"
        "(nome conforme detectado na consulta)\n\n"
        "[QUEIXA PRINCIPAL]\n"
        "(palavras do paciente)\n\n"
        "[HISTÓRIA DA DOENÇA ATUAL]\n"
        "(tempo de início, evolução, fatores agravantes e atenuantes, tratamentos anteriores)\n\n"
        "[DADOS VITAIS]\n"
        "- Altura:\n- Peso:\n- IMC:\n- PA:\n- FC:\n- Temperatura:\n- Saturação O2:\n\n"
        "[MEDICAMENTOS EM USO]\n"
        "(nome do medicamento – dose – frequência)\n\n"
        "[ALERGIAS]\n"
        "(a medicamentos, alimentos e ambientais – tipo de reação)\n\n"
        "[PATOLOGIAS PREGRESSAS]\n"
        "(diabetes, hipertensão, dislipidemia, doenças autoimunes, etc)\n\n"
        "[CIRURGIAS PRÉVIAS]\n"
        "(tipo de cirurgia – ano – intercorrências)\n\n"
        "[HISTÓRICO FAMILIAR]\n"
        "(câncer, diabetes, hipertensão, doenças neurológicas, etc)\n\n"
        "[ESTILO DE VIDA]\n"
        "- Álcool:\n- Tabagismo:\n- Atividade física:\n- Sono:\n\n"
        "[HIPÓTESES DIAGNÓSTICAS]\n"
        "(baseadas na queixa e achados)\n\n"
        "[CONDUTA / PLANO]\n"
        "(exames solicitados, medicamentos prescritos, orientações)\n"
        "---"
    )

    def generate_anamnesis(
        self,
        transcription: str,
        previous_anamnesis: Optional[str] = None,
        custom_prompt: Optional[str] = None
    ) -> str:
        """
        Gera ou atualiza a anamnese estruturada a partir da transcrição.
        
        Essa é a funcionalidade central do IPagent:
        - Escuta a transcrição acumulada
        - Preenche automaticamente o prontuário
        - Atualiza incrementalmente a cada chamada
        
        Args:
            transcription: Texto transcrito acumulado da consulta
            previous_anamnesis: Anamnese gerada anteriormente (para atualização incremental)
            custom_prompt: Prompt personalizado do médico (opcional)
        
        Returns:
            Anamnese estruturada preenchida
        """
        if not self._is_available:
            return "⚠️ Modelo não carregado. Aguarde a inicialização."

        if not transcription or len(transcription.strip()) < 20:
            return "⚠️ Transcrição muito curta para gerar anamnese."

        prompt = custom_prompt or self.DEFAULT_ANAMNESIS_PROMPT

        # Construir mensagem
        user_content = prompt + "\n\n"

        if previous_anamnesis and len(previous_anamnesis.strip()) > 50:
            user_content += (
                "=== ANAMNESE ANTERIOR (atualize com novas informações) ===\n"
                f"{previous_anamnesis}\n\n"
            )

        user_content += (
            "=== TRANSCRIÇÃO DA CONSULTA ===\n"
            f"{transcription}\n\n"
            "Preencha o prontuário acima com base na transcrição:"
        )

        try:
            response = self._llm.create_chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Você é um documentador médico. Sua tarefa é preencher "
                            "um prontuário estruturado a partir da transcrição de uma "
                            "consulta médica. Preencha APENAS com informações que "
                            "foram ditas na consulta. Mantenha o formato estruturado."
                        )
                    },
                    {"role": "user", "content": user_content}
                ],
                max_tokens=2048,
                temperature=0.1,  # Baixa para ser fiel à transcrição
            )

            anamnesis = response["choices"][0]["message"]["content"].strip()

            # Limpeza básica
            # Remove prefixos que o modelo pode adicionar
            prefixes_to_remove = [
                "aqui está a anamnese preenchida:",
                "anamnese preenchida:",
                "prontuário preenchido:",
                "com base na transcrição:",
            ]
            lower_anamnesis = anamnesis.lower()
            for prefix in prefixes_to_remove:
                if lower_anamnesis.startswith(prefix):
                    anamnesis = anamnesis[len(prefix):].strip()
                    break

            return anamnesis

        except Exception as e:
            logger.error(f"Erro ao gerar anamnese: {e}")
            if previous_anamnesis:
                return previous_anamnesis  # Retorna a anterior se falhar
            return f"⚠️ Erro ao gerar anamnese: {e}"

    @property
    def is_available(self) -> bool:
        return self._is_available
