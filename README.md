# Visão Geral

Esta solução implementa uma estrutura robusta para responder perguntas humanas diretamente contra seu banco SQL Server, gerando consultas SQL seguras, executando-as e retornando respostas bem estruturadas com opção de relatório.

Componentes principais:
- `extract_sql_data.py`: extrai o esquema e exemplos para apoiar o contexto.
- `train.py`: cria índice de embeddings FAISS do esquema (opcional, útil para exploração e documentação).
- `ask.py`: CLI de pergunta → SQL seguro → execução → resposta estruturada.
- `config.py`: centraliza configuração, credenciais e validações.

Principais garantias:
- Geração de SQL somente leitura (apenas `SELECT`), com bloqueio de palavras-chave perigosas.
- Limite de linhas configurável, com aplicação automática de `TOP`.
- Respostas estruturadas com amostra dos dados e resumo estatístico.
- Relatório opcional (CSV truncado) para exportação/inspeção rápida.

# Instalação

- Requisitos: `Python 3.10+`, ODBC Driver 17 para SQL Server, acesso de rede ao banco.
- Instale dependências:
  ```
  pip install -r requirements.txt
  ```
- Configure variáveis de ambiente (arquivo `.env` na raiz é suportado):
  - `OPENAI_API_KEY` (obrigatório)
  - `SERVER_DB` (obrigatório)
  - `DATABASE` (obrigatório)
  - `USER_DB` (obrigatório)
  - `PASS_DB` (obrigatório)
  - `ODBC_DRIVER` (opcional, padrão: `ODBC Driver 17 for SQL Server`)
  - `OPENAI_MODEL` (opcional, padrão: `gpt-3.5-turbo`)
  - `OPENAI_EMBEDDINGS_MODEL` (opcional, padrão: `text-embedding-ada-002`)
  - `ALLOWED_TABLES` (opcional: lista separada por vírgula para restringir as tabelas)

Exemplo `.env`:
```
OPENAI_API_KEY=...
SERVER_DB=servidor\instancia
DATABASE=MeuBanco
USER_DB=usuario
PASS_DB=senha
ALLOWED_TABLES=SE1010,SB1010,SA1010,SD1010,SF2010,SF1010,SE2010
```

# Como Funciona

- O `ask.py` carrega credenciais, descobre o esquema (`INFORMATION_SCHEMA.COLUMNS`), orienta o modelo a gerar SQL Server seguro, valida a consulta (apenas `SELECT`), aplica limite de linhas, executa via `SQLAlchemy/pyodbc` e monta uma resposta.
- A resposta inclui:
  - `pergunta`
  - `sql` (consulta final executada)
  - `amostra` (até 20 linhas)
  - `resumo` (estatísticas básicas por tipo)
  - `relatorio` (opcional: CSV truncado para inspeção)

# Uso

- Extrair esquema e exemplos (opcional, recomendado para documentação):
  ```
  python extract_sql_data.py
  ```
- Treinar índice de embeddings (opcional):
  ```
  python train.py
  ```
- Perguntar ao banco:
  ```
  python ask.py "Qual o faturamento médio por mês em 2024?" --limit 500 --report
  ```

- Parâmetros:
  - `pergunta`: texto livre em português.
  - `--limit`: limite de linhas aplicadas automaticamente (padrão: 500).
  - `--report`: inclui relatório CSV truncado na saída.

# Estrutura de Resposta

Exemplo de saída resumida:
```
Pergunta: Qual o faturamento médio por mês em 2024?
SQL: SELECT TOP 500 ...
Resumo: {'linhas': '12', 'colunas': '3', 'estatisticas_numericas': {...}}
Amostra:
{'mes': '2024-01', 'faturamento': 12345.67}
{'mes': '2024-02', 'faturamento': 23456.78}
...
Relatório:
mes,faturamento
2024-01,12345.67
...
```

# Boas Práticas e Segurança

- `ALLOWED_TABLES` restringe as tabelas elegíveis; configure para reduzir risco.
- O validador rejeita consultas com `UPDATE`, `DELETE`, `INSERT`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE`, `GRANT`, `EXEC`, `MERGE`.
- O limite de linhas é aplicado automaticamente com `TOP`, evitando respostas gigantes.
- Não armazene credenciais em código; use `.env` e variáveis de ambiente.

# Estrutura do Projeto

- `ask.py`: entrada principal de perguntas.
- `config.py`: configuração e criação de engine.
- `extract_sql_data.py`: geração de dataset de esquema.
- `train.py`: construção de índice FAISS do esquema.
- `outputs/`: índice FAISS (ignorado pelo Git).
- `dataset/`: arquivo `sql_schema.jsonl` gerado pelo extrator.

# Troubleshooting

- Erro de ODBC: confirme o `ODBC Driver 17` instalado e que o `SERVER_DB` está acessível.
- `OPENAI_API_KEY` ausente: crie o `.env` ou exporte no ambiente.
- Tabelas não encontradas: configure `ALLOWED_TABLES` ou garanta acesso ao esquema `dbo`.

