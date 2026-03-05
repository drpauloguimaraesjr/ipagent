"""
Script utilitário para importar acervos antigos de consultas (ex: Paludnote/Evernote)
Este script permite jogar milhares de transcrições antigas direto para a base de conhecimento
e formato de treinamento do IPagent.
"""

import os
import json
import logging
import argparse
from pathlib import Path
from tqdm import tqdm

from config import load_config
from core.memory import KnowledgeMemory
from training.data_collector import DataCollector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Importador")

def import_text_files(directory_path: str):
    """
    Importa arquivos .txt ou .md de um diretório.
    Assume que cada arquivo é uma consulta transcrita.
    """
    config = load_config()
    target_dir = Path(directory_path)
    
    if not target_dir.exists() or not target_dir.is_dir():
        logger.error(f"Diretório {directory_path} não encontrado.")
        return

    # 1. Inicializa Conectores
    memory = KnowledgeMemory(config.memory)
    memory.initialize()
    
    collector = DataCollector(config.training)
    
    files = list(target_dir.glob("*.txt")) + list(target_dir.glob("*.md"))
    logger.info(f"Encontrados {len(files)} arquivos de consulta para importar!")
    
    sucesso_memoria = 0
    
    for file_path in tqdm(files, desc="Importando consultas"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                conteudo = f.read()
            
            # Pega o nome do arquivo pra usar como metadado/data
            filename = file_path.stem
            
            # --- 1. Adicionar ao Banco de Dados de Pesquisa (RAG) ---
            if memory.add_consultation(
                transcription=conteudo,
                notes=f"Importado de: {filename}",
                date=filename # idealmente o nome do arquivo tem a data
            ):
                sucesso_memoria += 1
                
            # --- 2. Adicionar ao Dataset de Fine-Tuning ---
            # Aqui podemos criar um exemplo onde o LLM tenta prever a nota
            # baseado na transcrição (Se os arquivos estiverem divididos)
            # Para arquivos brutos, podemos usar como "correção de transcrição" perfeita
            collector.add_transcription_correction(
                original_transcription=conteudo[:500] + "...", # simula um erro
                corrected_transcription=conteudo, # O texto real vira o alvo do aprendizado
                quality_score=1.0
            )
            
        except Exception as e:
            logger.error(f"Erro lendo arquivo {file_path}: {e}")

    logger.info("="*40)
    logger.info("🎉 IMPORTAÇÃO CONCLUÍDA 🎉")
    logger.info(f"📥 {sucesso_memoria} consultas injetadas na Memória Local.")
    logger.info(f"🧠 Dataset preparado e pronto para o script de Fine-Tuning!")
    logger.info("="*40)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Importa acervo de consultas para o IPagent')
    parser.add_argument('diretorio', type=str, help='Caminho para a pasta com os arquivos .txt/.md')
    args = parser.parse_args()
    
    import_text_files(args.diretorio)
