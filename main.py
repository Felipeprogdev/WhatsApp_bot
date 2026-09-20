import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
import httpx
from fastapi import FastAPI, Request
from groq_IA import extrair_dados_globais  # IA para extrair informações do texto
from gerador_pdf import gerar_pdf_orcamento


app = FastAPI()

# --- Configurações Gerais ---
NODE_BOT_URL = "http://localhost:3000"  # Servidor Node.js que envia as mensagens
TEMPO_DEBOUNCE_SEGUNDOS = 5.0  # Espera para agrupar mensagens seguidas
TEMPO_COOLDOWN_MINUTOS = 20  # Bloqueio temporário para assuntos fora do escopo
BOT_START_TIME = datetime.now(timezone.utc)  # Data/hora de inicialização para ignorar mensagens antigas

ARQUIVO_RELATORIO = "relatorio_diario.json"  # Registro em arquivo dos pedidos concluídos

# --- Estados em Memória ---
buffer_mensagens = {}  # Mensagens aguardando a janela de debounce: { user_id: { "mensagens": [...], "task": asyncio.Task } }
db_usuarios = {}  # Dados da sessão do usuário: { user_id: { "nome": ..., "pedido": ..., ... } }
usuarios_processando = set()  # Trava contra processamento simultâneo do mesmo ID


# ==============================================================================
# MANIPULAÇÃO DO ARQUIVO DE BLOQUEIO DIÁRIO (JSON)
# ==============================================================================

def carregar_relatorio_diario() -> dict:
    """Lê o arquivo relatorio_diario.json e retorna como dicionário."""
    if os.path.exists(ARQUIVO_RELATORIO):
        try:
            with open(ARQUIVO_RELATORIO, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Erro ao ler {ARQUIVO_RELATORIO}: {e}")
            return {}
    return {}


def salvar_usuario_no_relatorio(user_id: str, dados_finalizados: dict):
    """Salva o pedido finalizado no arquivo JSON incluindo a data no formato YYYY-MM-DD."""
    relatorio = carregar_relatorio_diario()
    data_hoje_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    relatorio[user_id] = {
        "nome": dados_finalizados.get("nome"),
        "pedido": dados_finalizados.get("pedido"),
        "endereco": dados_finalizados.get("endereco"),
        "visita": dados_finalizados.get("visita_txt"),
        "data_finalizacao": data_hoje_str
    }

    try:
        with open(ARQUIVO_RELATORIO, "w", encoding="utf-8") as f:
            json.dump(relatorio, f, ensure_ascii=False, indent=4)
        print(f"💾 Usuário {user_id} registrado no relatório na data {data_hoje_str}.")
    except Exception as e:
        print(f"❌ Erro ao salvar relatório: {e}")


def usuario_bloqueado_por_relatorio(user_id: str) -> bool:
    """
    Retorna True se o usuário finalizou pedido NA DATA DE HOJE.
    Libera automaticamente (retorna False) caso já seja outro dia.
    """
    relatorio = carregar_relatorio_diario()
    if user_id in relatorio:
        data_finalizacao = relatorio[user_id].get("data_finalizacao")
        if data_finalizacao:
            hoje_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            return data_finalizacao == hoje_str  # Bloqueado apenas se as datas forem iguais
    return False


# ==============================================================================
# ENVIO DE MENSAGENS E PROCESSAMENTO
# ==============================================================================

async def enviar_whatsapp(numero: str, texto: str):
    """Dispara a mensagem de resposta via API Node.js."""
    payload = {"number": numero, "message": texto}
    try:
        async with httpx.AsyncClient() as http_client:
            await http_client.post(f"{NODE_BOT_URL}/send-message", json=payload, timeout=10.0)
    except Exception as e:
        print(f"❌ Falha ao enviar para {numero}: {e}")


async def aguardar_e_processar(user_id: str):
    """Aguarda o tempo de debounce, processa o buffer de mensagens via IA,

    gerencia o cooldown/bloqueios e conduz o funil de atendimento até a geração
    do PDF.
    """
    # 1. Aguarda o tempo de agrupamento de mensagens (debounce) para evitar disparos repetidos
    await asyncio.sleep(TEMPO_DEBOUNCE_SEGUNDOS)

    # 2. Trava de segurança: cancela a execução se o buffer do usuário foi limpo ou se já está em processamento
    if user_id not in buffer_mensagens or user_id in usuarios_processando:
        return

    # Registra o usuário no conjunto de processamentos ativos
    usuarios_processando.add(user_id)

    try:
        # 3. Consolidação de mensagens: extrai o histórico pendente do buffer e junta em uma única string
        lista_mensagens = buffer_mensagens[user_id]["mensagens"]
        texto_unificado = " ".join(lista_mensagens).strip()

        # Limpa o buffer do usuário para estar pronto para futuras mensagens
        del buffer_mensagens[user_id]

        # Obtém o timestamp atual em UTC para validações de tempo/cooldown
        agora = datetime.now(timezone.utc)

        # 4. Checa se o usuário já concluiu um atendimento no dia de hoje (evita múltiplos orçamentos no mesmo dia)
        if usuario_bloqueado_por_relatorio(user_id):
            print(f"🚫 {user_id} bloqueado: pedido já finalizado hoje.")
            return

        # 5. Recupera os dados cadastrais atuais do dicionário em memória ou inicializa a estrutura padrão
        dados_usuario = db_usuarios.get(
            user_id,
            {
                "e_comigo": None,
                "nome": None,
                "pedido": None,
                "endereco": None,
                "visita_txt": None,
                "bloqueado_ate": None,
            },
        )

        # 6. Verifica se o usuário está cumprindo o período de suspensão temporária (cooldown de 20 min)
        if (
            dados_usuario.get("bloqueado_ate")
            and agora < dados_usuario["bloqueado_ate"]
        ):
            return

        # 7. Chamada ao serviço de IA (Groq): analisa o texto unificado e atualiza o estado do JSON do cliente
        dados_atualizados = extrair_dados_globais(
            texto_unificado, dados_usuario
        )

        # 8. Trata mensagens fora de escopo (trotes, desabafos, assuntos não relacionados a marcenaria)
        if str(dados_atualizados.get("e_comigo", "")).strip().lower() in [
            "não",
            "nao",
        ]:
            # Aplica o cooldown adicionando 20 minutos ao horário atual
            dados_usuario["bloqueado_ate"] = agora + timedelta(
                minutes=TEMPO_COOLDOWN_MINUTOS
            )
            db_usuarios[user_id] = dados_usuario
            print(f"⏸️ {user_id} em cooldown por 20 minutos.")
            return

        # 9. Atualiza o banco de dados local com as novas informações validadas
        db_usuarios[user_id] = dados_atualizados

        # Extrai os dados cadastrais atualizados do dicionário
        nome = dados_atualizados.get("nome")
        pedido = dados_atualizados.get("pedido")
        endereco = dados_atualizados.get("endereco")
        visita_txt = dados_atualizados.get("visita_txt")

        # Exibe no terminal a identificação do cliente em atendimento
        print(f"👤 Cliente: {nome or 'Novo usuário'}")

        # --- FLUXO DO FUNIL DE ATENDIMENTO ---

        # ETAPA 1: Solicitando o nome caso ainda não esteja preenchido
        if nome is None:
            resposta = (
                "Olá! Bem-vindo à RFA Móveis Planejados. 🪚✨\n"
                "Somos especialistas em móveis planejados e marcenaria sob medida.\n\n"
                "Para começarmos o seu atendimento, por favor, me informe o seu *nome*:"
            )
            await enviar_whatsapp(user_id, resposta)
            return

        # ETAPA 2: Solicitando o pedido/projeto caso o nome já exista mas o pedido esteja ausente
        if pedido is None:
            await enviar_whatsapp(
                user_id,
                f"Olá, {nome}! Bem-vindo à RFA Móveis Planejados. 🪚✨\n"
                "O que você deseja projetar ou fazer conosco?",
            )
            return

        # ETAPA 3: Solicitando o endereço completo caso o pedido já tenha sido coletado
        if endereco is None:
            await enviar_whatsapp(
                user_id,
                "Perfeito! Qual o seu *endereço completo* para entrega/visita?",
            )
            return

        # --- CONCLUSÃO DO ATENDIMENTO ---
        # Todas as informações obrigatórias foram coletadas (nome, pedido e endereço)

        # Define a mensagem final variando se haverá visita técnica presencial
        if visita_txt == "Sim":
            resposta_final = (
                f"Tudo certo, {nome}! 👌\n\n"
                "Obrigado! Nossa equipe entrará em contato para passar o orçamento e agendar a visita para a medição."
            )
        else:
            resposta_final = (
                f"Tudo certo, {nome}! 👌\n\n"
                "Obrigado! Nossa equipe entrará em contato para passar o orçamento."
            )

        # 📄 Executa a geração do relatório em PDF contendo o resumo dos dados cadastrados
        gerar_pdf_orcamento(dados_atualizados)

        # Envia a confirmação textual de finalização para o cliente via WhatsApp
        await enviar_whatsapp(user_id, resposta_final)

        # Registra a conclusão no histórico/relatório para aplicar o bloqueio diário
        salvar_usuario_no_relatorio(user_id, dados_atualizados)

    finally:
        # Garante a remoção do usuário da lista de processamento ativo, permitindo futuras interações
        usuarios_processando.discard(user_id)


# ==============================================================================
# WEBHOOK DE ENTRADA
# ==============================================================================

@app.post("/webhook")
async def webhook(request: Request):
    payload = await request.json()

    raw_push_name = payload.get("pushName")
    nome_contato = (
        raw_push_name.strip()
        if raw_push_name and isinstance(raw_push_name, str) and raw_push_name.strip()
        else payload.get("contact_name")
    )

    user_id = payload.get("user_id", "")
    texto_mensagem = payload.get("text", "").strip()
    msg_timestamp = payload.get("timestamp")

    # Descarta mensagens enviadas antes de o servidor iniciar
    if msg_timestamp:
        msg_date = datetime.fromtimestamp(msg_timestamp, tz=timezone.utc)
        if msg_date < BOT_START_TIME:
            return {"status": "ignored_old_message"}

    if not user_id or not texto_mensagem:
        return {"status": "empty_payload"}

    # Bloqueia se o cliente já concluiu atendimento no mesmo dia
    if usuario_bloqueado_por_relatorio(user_id):
        print(f"🚫 {user_id} ignorado: pedido concluído hoje.")
        return {"status": "user_completed_today"}

    # Inicializa cadastro no dicionário local
    if user_id not in db_usuarios:
        db_usuarios[user_id] = {
            "e_comigo": None, "nome": nome_contato, "pedido": None,
            "endereco": None, "visita_txt": None, "bloqueado_ate": None
        }

    # Verifica se está no cooldown de 20 minutos
    dados_usuario = db_usuarios.get(user_id, {})
    bloqueado_ate = dados_usuario.get("bloqueado_ate")
    if bloqueado_ate and datetime.now(timezone.utc) < bloqueado_ate:
        return {"status": "user_in_cooldown"}

    # Aplica lógica de Debounce (reinicia a contagem a cada nova mensagem do mesmo usuário)
    if user_id in buffer_mensagens:
        buffer_mensagens[user_id]["task"].cancel()
        buffer_mensagens[user_id]["mensagens"].append(texto_mensagem)
    else:
        buffer_mensagens[user_id] = {"mensagens": [texto_mensagem], "task": None}

    task = asyncio.create_task(aguardar_e_processar(user_id))
    buffer_mensagens[user_id]["task"] = task

    return {"status": "queued"}