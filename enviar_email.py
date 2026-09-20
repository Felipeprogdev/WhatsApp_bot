import os
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication


def enviar_pdf_para_mim(caminho_completo_pdf: str, caminho_json_key: str = "email_key.json"):
    """
    Envia um arquivo PDF para o próprio e-mail do Gmail recebendo o caminho completo do arquivo.

    :param caminho_completo_pdf: Caminho absoluto/completo do arquivo PDF.
    :param caminho_json_key: Caminho do arquivo JSON com as credenciais.
    """
    # 1. Extrai apenas o nome do arquivo do caminho completo
    nome_arquivo = os.path.basename(caminho_completo_pdf)

    # 2. Verificar se os arquivos existem no sistema
    if not os.path.exists(caminho_json_key):
        raise FileNotFoundError(f"Erro: O arquivo de chaves '{caminho_json_key}' não foi encontrado.")

    if not os.path.exists(caminho_completo_pdf):
        raise FileNotFoundError(f"Erro: O arquivo PDF não foi encontrado em '{caminho_completo_pdf}'.")

    # 3. Carregar as credenciais do JSON
    with open(caminho_json_key, 'r', encoding='utf-8') as f:
        credenciais = json.load(f)

    meu_email = credenciais.get("email")
    email_key = credenciais.get("email_key")

    if not meu_email or not email_key:
        raise ValueError("O arquivo JSON precisa conter as chaves 'email' e 'email_key'.")

    # Remove espaços da chave do Google caso existam
    email_key = email_key.replace(" ", "")

    # 4. Montar a estrutura da mensagem
    msg = MIMEMultipart()
    msg['From'] = meu_email
    msg['To'] = meu_email  # Envia para você mesmo
    msg['Subject'] = f"PDF em Anexo: {nome_arquivo}"

    corpo = f"Olá!\n\nEm anexo está o arquivo PDF solicitado: {nome_arquivo}."
    msg.attach(MIMEText(corpo, 'plain', 'utf-8'))

    # 5. Ler e anexar o arquivo PDF pelo caminho completo
    with open(caminho_completo_pdf, 'rb') as arquivo_pdf:
        anexo = MIMEApplication(arquivo_pdf.read(), _subtype="pdf")
        anexo.add_header(
            'Content-Disposition',
            'attachment',
            filename=nome_arquivo
        )
        msg.attach(anexo)

    # 6. Conectar ao servidor SMTP do Gmail e enviar
    servidor_smtp = "smtp.gmail.com"
    porta = 587

    try:
        servidor = smtplib.SMTP(servidor_smtp, porta)
        servidor.starttls()  # Ativa criptografia TLS
        servidor.login(meu_email, email_key)
        servidor.sendmail(meu_email, meu_email, msg.as_string())
        servidor.quit()

        print(f"Sucesso! O arquivo '{nome_arquivo}' foi enviado com sucesso para {meu_email}.")

    except smtplib.SMTPAuthenticationError:
        print("Erro de autenticação: Verifique se o e-mail e a email_key no JSON estão corretos.")
    except Exception as e:
        print(f"Ocorreu um erro ao enviar o e-mail: {e}")


# --- Exemplo de Chamada ---
if __name__ == "__main__":
    pass