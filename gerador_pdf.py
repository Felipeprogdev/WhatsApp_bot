from datetime import datetime
import locale
import os
import re
import unicodedata
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from enviar_email import enviar_pdf_para_mim


# Tenta configurar a localização em português para obter o nome do mês por extenso
try:
    locale.setlocale(locale.LC_TIME, "pt_BR.UTF-8")
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, "pt_BR")
    except locale.Error:
        pass


def obter_nome_mes_atual() -> str:
    """Retorna o nome do mês atual em português, com mapeamento manual como fallback."""
    meses = {
        1: "janeiro",
        2: "fevereiro",
        3: "março",
        4: "abril",
        5: "maio",
        6: "junho",
        7: "julho",
        8: "agosto",
        9: "setembro",
        10: "outubro",
        11: "novembro",
        12: "dezembro",
    }
    agora = datetime.now()
    return meses.get(agora.month, agora.strftime("%B").lower())


def remover_acentos_e_caracteres(texto: str) -> str:
    """Remove acentos e caracteres especiais, mantendo apenas letras, números e hífens/underlines."""
    nfkd = unicodedata.normalize("NFKD", texto)
    texto_sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    texto_limpo = re.sub(r"[^\w\s-]", "", texto_sem_acento).strip()
    return texto_limpo.replace(" ", "_")


def gerar_pdf_orcamento(dados: dict, caminho_saida: str = None) -> str:
    """Gera um PDF de confirmação de orçamento/pedido para marcenaria."""
    nome_bruto = dados.get("nome") or "Nao_informado"
    pedido = dados.get("pedido") or "Não informado"
    endereco = dados.get("endereco") or "Não informado"
    visita_txt = dados.get("visita_txt") or "Não informado"

    # Define a pasta dinâmica de saída (ex: "PDFS de setembro")
    if not caminho_saida:
        nome_mes = obter_nome_mes_atual()
        pasta_destino = os.path.join(os.getcwd(), f"PDFS de {nome_mes}")

        # Cria a pasta caso ela não exista
        os.makedirs(pasta_destino, exist_ok=True)

        data_formatada = datetime.now().strftime("%d-%m")
        nome_sanitizado = remover_acentos_e_caracteres(nome_bruto)
        nome_arquivo = f"{nome_sanitizado}_{data_formatada}.pdf"
        caminho_saida = os.path.join(pasta_destino, nome_arquivo)

    # Configuração do Documento PDF
    doc = SimpleDocTemplate(
        caminho_saida,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    elements = []
    styles = getSampleStyleSheet()

    # --- ESTILOS PERSONALIZADOS ---
    estilo_titulo = ParagraphStyle(
        "TituloEmpresa",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#2C3E50"),
    )

    estilo_subtitulo = ParagraphStyle(
        "Subtitulo",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=12,
        textColor=colors.HexColor("#7F8C8D"),
    )

    estilo_label = ParagraphStyle(
        "Label",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#34495E"),
    )

    estilo_valor = ParagraphStyle(
        "Valor",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#2C3E50"),
    )

    # --- CABEÇALHO ---
    elements.append(Paragraph("RFA MÓVEIS PLANEJADOS", estilo_titulo))
    elements.append(
        Paragraph("Móveis Sob Medida & Marcenaria", estilo_subtitulo)
    )
    elements.append(
        Paragraph(
            f"Data de Emissão: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            estilo_subtitulo,
        )
    )
    elements.append(Spacer(1, 15))

    # Linha divisória
    elements.append(
        HRFlowable(
            width="100%",
            thickness=2,
            color=colors.HexColor("#D35400"),
            spaceAfter=15,
        )
    )

    # --- TABELA COM OS DADOS DO PEDIDO ---
    tabela_dados = [
        [
            Paragraph("Cliente:", estilo_label),
            Paragraph(str(nome_bruto), estilo_valor),
        ],
        [
            Paragraph("Endereço:", estilo_label),
            Paragraph(str(endereco), estilo_valor),
        ],
        [
            Paragraph("Solicitação / Pedido:", estilo_label),
            Paragraph(str(pedido), estilo_valor),
        ],
        [
            Paragraph("Visita Técnica:", estilo_label),
            Paragraph(str(visita_txt), estilo_valor),
        ],
    ]

    t = Table(tabela_dados, colWidths=[130, 410])
    t.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8F9FA")),
            ("PADDING", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BDC3C7")),
        ])
    )

    elements.append(t)
    elements.append(Spacer(1, 20))

    # --- RODAPÉ / OBSERVAÇÕES ---
    estilo_rodape = ParagraphStyle(
        "Rodape",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#7F8C8D"),
    )

    elements.append(
        Paragraph(
            "* Este documento confirma o registro inicial das informações solicitadas via WhatsApp.",
            estilo_rodape,
        )
    )
    elements.append(
        Paragraph(
            "* Nossa equipe técnica entrará em contato para validação de medidas e envio do orçamento detalhado.",
            estilo_rodape,
        )
    )

    # Constrói o PDF
    doc.build(elements)
    print(f"📄 PDF gerado com sucesso em: {caminho_saida}")
    enviar_pdf_para_mim(caminho_saida)


if __name__ == "__main__":
    pass