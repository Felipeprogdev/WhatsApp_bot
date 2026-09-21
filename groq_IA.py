import json
from groq import Groq

CAMINHO_JSON = "chave_do_groq.json"

with open(CAMINHO_JSON, "r", encoding="utf-8") as arquivo:
    dados_chave = json.load(arquivo)

GROQ_API_KEY = (dados_chave.get("Chave_groq"))


client_groq = Groq(api_key=GROQ_API_KEY)


def obter_modelos_de_texto() -> list:
    """Retorna apenas modelos de chat e texto, ignorando áudio e guardrails."""
    modelos_prioritarios = [
        "groq/compound",
        "groq/compound-mini",
        "qwen/qwen3.8-27b",
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b"
    ]

    try:
        modelos_api = [m.id for m in client_groq.models.list().data]
        modelos_validos = [m for m in modelos_prioritarios if m in modelos_api]

        if modelos_validos:
            return modelos_validos

        ignorar = ["whisper", "guard", "orpheus", "safeguard"]
        return [m for m in modelos_api if not any(term in m.lower() for term in ignorar)]

    except Exception as e:
        print(f"⚠️ Erro ao consultar modelos na conta: {e}")
        return ["groq/compound", "groq/compound-mini"]


def extrair_dados_globais(texto_usuario: str, dados_atuais: dict = None) -> dict:
    if dados_atuais is None:
        dados_atuais = {
            "e_comigo": None,
            "nome": None,
            "pedido": None,
            "endereco": None,
            "visita_txt": None,
        }

    prompt = f"""
    Sua tarefa é analisar a nova mensagem enviada pelo cliente de uma marcenaria e atualizar o JSON de cadastro.

    DADOS ATUAIS JÁ COLETADOS:
    {json.dumps(dados_atuais, ensure_ascii=False)}

    REGRAS PARA A VARIÁVEL 'e_comigo' (ATENÇÃO RÍGIDA):
    1. Se 'e_comigo' no JSON atual já for "Não", MANTENHA "Não".
    2. Defina "e_comigo": "Não" INDEPENDENTE de ter nome cadastrado ou não se a mensagem for:
       - Desabafo pessoal, conversas profundas/emocionais (ex: "ninguém me ama", "sou insuficiente").
       - Trotes, brincadeiras, piadas ou assuntos totalmente alheios a comércio/marcenaria (ex: figurinhas, memes, futebol, política).
       - Mensagens desconexas ou tentativas de confundir a IA.

    3. Defina "e_comigo": "Sim" APENAS se a mensagem for:
       - Saudações normais de atendimento ("Oi", "Olá", "Boa tarde", "Tudo bem?").
       - Apresentação de nome ("Meu nome é João").
       - Qualquer mensagem que trate de orçamentos, pedidos, móveis, projetos, prazos ou visitas técnicas.

    REGRAS DE ATUALIZAÇÃO DOS CAMPOS:
    - Mantenha os valores existentes no JSON se a mensagem não trouxer novos dados.
    - Se o cliente fornecer nome, pedido, endereço ou preferências de visita, atualize os respectivos campos.
    - Caso tenha erros de gramática, coloque a mensagem digitada atras e logo na frente entre parenteses () a mensagem com as correções gramaticais, exemplo "armario 4 portad" APENAS NO PEDIDO ESSA CORREÇÃO GRAMATICAL

    Regras para 'visita_txt':
    - Retorne "Sim" se o cliente pedir visita explicitamente ou se faltarem medidas do projeto.
    - Retorne "Não" se o cliente já forneceu todas as dimensões.

    Chaves obrigatórias do JSON:
    - e_comigo: "Sim" ou "Não"
    - nome: string ou null
    - pedido: string ou null
    - endereco: string ou null
    - visita_txt: "Sim", "Não"

    Responda EXCLUSIVAMENTE em formato JSON válido, sem texto adicional.

    Nova mensagem do cliente: "{texto_usuario}"
    """

    modelos = obter_modelos_de_texto()

    for modelo in modelos:
        try:
            response = client_groq.chat.completions.create(
                model=modelo,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.1,
            )

            conteudo = response.choices[0].message.content
            if conteudo and conteudo.strip():
                return json.loads(conteudo)

        except Exception as e:
            print(f"⚠️ Falha ao tentar com o modelo '{modelo}': {e}")

    # Retorna o estado atual mantendo a consistência caso ocorra falha na API
    return dados_atuais


if __name__ == "__main__":
    pass
