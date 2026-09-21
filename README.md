# 🪚 Bot de Atendimento Automático - RFA Móveis Planejados

Este projeto é uma solução inteligente de atendimento via WhatsApp para marcenarias e empresas de móveis planejados. Ele utiliza **FastAPI** para receber e processar as mensagens via Webhook, integração com modelos de **IA da Groq** para extração inteligente de dados em linguagem natural, geração de **PDFs estilizados** via ReportLab e envio automático do resumo por **e-mail via SMTP**.

## 🚀 Funcionalidades

* **Funil de Atendimento Inteligente:** Coleta progressiva de dados essenciais: Nome, Descrição do Pedido, Endereço e Necessidade de Visita Técnica.

* **Processamento de Linguagem Natural (NLP):** Utiliza a API do Groq para entender mensagens informais e realizar pequenas correções gramaticais na descrição do pedido.

* **Sistema de Debounce (5s):** Aguarda o cliente terminar de digitar mensagens seguidas antes de enviar ao processamento, economizando requisições.

* **Filtro de Conteúdo Fora do Escopo & Cooldown:** Detecta desabafos, piadas ou assuntos não relacionados e aplica uma pausa/cooldown temporário de **20 minutos**.

* **Bloqueio de Múltiplos Atendimentos Diários:** Registra o histórico no arquivo `relatorio_diario.json` para evitar duplicidade de cadastros do mesmo usuário dentro de **24 horas** (no mesmo dia civil).

* **Geração e Envio de PDF:** Cria um arquivo PDF personalizado do orçamento com base na data/mês e o envia automaticamente para o e-mail da empresa.

## 🛠️ Tecnologias Utilizadas

* **Python 3.10+** (FastAPI, Uvicorn, ReportLab, Groq SDK, HTTPX)

* **Node.js** (Integração e envio de mensagens no WhatsApp)

* **SMTP/smtplib** (Envio automático de e-mails)

## 📋 Pré-requisitos e Configuração de Chaves

Antes de executar a aplicação, você precisa criar e configurar os arquivos JSON com suas credenciais na raiz do projeto.

### 1. Configurar Chave da API da Groq

Crie um arquivo chamado **`chave_do_groq.json`** no diretório raiz do projeto com o seguinte formato:

```json
{
  "Chave_groq": "SUA_CHAVE_API_DA_GROQ_AQUI"
}
```

> 💡 *Você pode obter sua chave gratuitamente no painel da [Groq Cloud](https://console.groq.com/?utm_source=gemini).*

### 2. Configurar Credenciais de E-mail

Crie um arquivo chamado **`email_key.json`** no diretório raiz com as informações da sua conta do Gmail:

```json
{
  "email": "seu_email@gmail.com",
  "email_key": "sua_senha_de_app_do_google"
}
```

> ⚠️ **Atenção:** Em `email_key`, utilize uma **Senha de App** gerada nas configurações de segurança do Google, e não a sua senha pessoal do e-mail.

### 3. Registro e Bloqueio Diário (`relatorio_diario.json`)

O arquivo **`relatorio_diario.json`** é gerado e atualizado automaticamente pela aplicação.

* Ele atua como um sistema de persistência para evitar que o robô continue enviando mensagens de atendimento para um cliente que já concluiu o pedido no dia vigente.

* A liberação ocorre automaticamente quando a data do sistema muda para o dia seguinte.

## 🔧 Instalação e Execução

Para rodar a aplicação completa, você precisará manter dois serviços rodando em paralelo no terminal: o servidor Python (FastAPI) e o robô do WhatsApp em Node.js.

### 1. Configurar e rodar o Servidor Python (FastAPI)

1. **Clone o repositório:**

   ```bash
   git clone https://github.com/seu-usuario/seu-repositorio.git
   cd seu-repositorio
   ```

2. **Crie e ative um ambiente virtual:**

   ```bash
   python -m venv venv
   # No Windows:
   venv\Scripts\activate
   # No Linux/Mac:
   source venv/bin/activate
   ```

3. **Instale todas as dependências Python:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Instale o WhatsApp Web e as dependências auxiliares:**
   ```bash
   npm install whatsapp-web.js qrcode-terminal express axios


5. **Inicie o servidor Webhook (FastAPI):**

   ```bash
   uvicorn main:app --reload --port 8000
   ```

### 2. Iniciar o Bot do WhatsApp (Node.js)

Em um **novo terminal**, navegue até a pasta do projeto (ou pasta do bot Node) e execute o script para conectar com o WhatsApp:

```bash
node bot.js
```

> ⚠️ **Nota:** Certifique-se de ter o Node.js instalado e de rodar o `npm install` caso haja dependências `node_modules` necessárias para o `bot.js`.

---

### 📱 Troca de Conta / Sessão do WhatsApp (`.wwebjs_auth`)

Ao escanear o QR Code pela primeira vez, o servidor cria automaticamente a pasta chamada **`.wwebjs_auth`** para salvar os tokens da sessão ativa do WhatsApp Web.

* **Como trocar o número do WhatsApp conectado:** 
  Se você desejar trocar de conta ou reescanear o QR Code, **delete a pasta `.wwebjs_auth`** antes de executar o comando `node bot.js` novamente.

---

## 📂 Estrutura de Arquivos

```
├── main.py                 # Ponto de entrada (API FastAPI, controle de estado, debounce e webhook)
├── groq_IA.py              # Integração com a IA Groq para interpretação e extração dos JSONs
├── gerador_pdf.py          # Módulo para construção do PDF estilizado com ReportLab
├── enviar_email.py         # Módulo SMTP para envio do PDF por e-mail
├── bot.js                  # Script Node.js para escutar e disparar mensagens via WhatsApp
├── requirements.txt        # Dependências do projeto Python para instalação com pip
├── chave_do_groq.json      # [Privado] Chave da API do Groq
├── email_key.json          # [Privado] Credenciais SMTP do Gmail
├── relatorio_diario.json   # Histórico de bloqueio de atendimentos diários concluídos
└── .wwebjs_auth/           # [Gerado automaticamente] Dados de autenticação do WhatsApp Web
```

## 📝 Licença

Este projeto é mantido para uso privado da **RFA Móveis Planejados**. Sinta-se à vontade para utilizar a estrutura como referência.
