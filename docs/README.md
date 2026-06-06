# Documentação — Backend ISCTools

## Índice

### Fluxos de dados
- [Autenticação](fluxos-de-dados/autenticacao.md) — registro, login JWT, OAuth Google
- [Chat e Streaming SSE](fluxos-de-dados/chat-e-streaming.md) — criação de conversa, envio de mensagem, eventos SSE
- [Knowledge Retrieval (RAG)](fluxos-de-dados/knowledge-retrieval.md) — busca semântica nas transcrições da disciplina

### AI Agent
- [Visão Geral](ai-agent/visao-geral.md) — stack, arquitetura ReAct, criação do agente
- [Ferramentas](ai-agent/ferramentas.md) — lista completa com parâmetros e gatilhos
- [System Prompt](ai-agent/prompts/system-prompt.md) — análise das seções do prompt e prompt de título

### Infra
- [Docker](infra/docker.md) — serviços, Dockerfiles, ordem de inicialização
- [Variáveis de Ambiente](infra/variaveis-de-ambiente.md) — todas as variáveis com defaults e descrições
- [Banco de Dados](infra/banco-de-dados.md) — diagrama ER, pgvector, sessões

### Como Rodar
- [Desenvolvimento](how-run/desenvolvimento.md) — setup, comandos do dia a dia, hot reload
- [Migrations](how-run/migrations.md) — fluxo para criar e aplicar migrations Alembic
