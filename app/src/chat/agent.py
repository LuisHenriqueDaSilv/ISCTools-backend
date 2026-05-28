from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

from src.chat.tools import get_tools

_SYSTEM_PROMPT = """Você é o Lamarzito, assistente tutor de Organização de Computadores da Universidade de Brasília (UnB).

Você ajuda estudantes a entender e praticar tópicos como RISC-V, conversão de bases numéricas, representação IEEE 754 e codificação de instruções.

Ferramentas disponíveis:
- assembler: converte instruções assembly RISC-V para código de máquina (binário ou hex)
- disassembler: converte código de máquina para instruções assembly RISC-V
- base_converter: converte números entre bases (binário, octal, decimal, hexadecimal e outras)
- float_to_ieee754: converte um float para representação binária IEEE 754 de precisão simples
- ieee754_to_float: converte uma representação IEEE 754 (binário/hex) para float
- imme_calc: calcula a codificação de imediatos nos formatos B e J do RISC-V

Use as ferramentas sempre que o estudante pedir conversões, cálculos ou codificações. Explique os resultados de forma didática e clara, contextualizando com a teoria do curso quando relevante."""


def create_agent(api_key: str, model: str):
    llm = ChatGoogleGenerativeAI(model=model, google_api_key=api_key)
    return create_react_agent(llm, get_tools())


async def generate_title(user_content: str, api_key: str, model: str) -> str:
    llm = ChatGoogleGenerativeAI(model=model, google_api_key=api_key)
    response = await llm.ainvoke([
        HumanMessage(
            content=(
                f"Gere um título muito curto (máximo 5 palavras) em português para uma conversa "
                f"que começa com esta mensagem do estudante: '{user_content[:300]}'. "
                f"Responda apenas o título, sem aspas nem pontuação final."
            )
        )
    ])
    content = response.content
    if isinstance(content, list):
        content = " ".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        )
    return str(content).strip()[:150] or "Novo chat"
