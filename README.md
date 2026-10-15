# 🎯 Simulados para Concurso Público

Aplicação **Streamlit** de simulados com foco em **análise de desempenho orientada a dados**,
acompanhada de um utilitário CLI/gráfico para gestão do banco de questões.

## Arquivos do projeto

| Arquivo            | Função                                                                 |
|--------------------|------------------------------------------------------------------------|
| `app.py`           | Interface do simulado (prova, cronômetro, resultados e log .txt)       |
| `parser_helper.py` | Utilitário para inserir/converter questões no padrão `questoes.json`   |
| `questoes.json`    | Banco de questões (criado automaticamente com exemplos se não existir) |

## Instalação

```bash
pip install streamlit
```

> Não há outras dependências: apenas `streamlit` e módulos da biblioteca padrão
> (`json`, `random`, `os`, `datetime`, `argparse`, `ast`, `sys`).

## Como executar

### Aplicação principal (simulado)

```bash
streamlit run app.py
```

- Escolha o modo: **Treino Livre (20 questões)** ou **Simulado Completo (50 questões)**.
- Filtre por matérias específicas ou deixe vazio para **sorteio misto proporcional**.
- Acompanhe o **cronômetro** e a **barra de progresso** durante a prova.
- Ao finalizar: pontuação total, % de acertos por matéria, revisão detalhada e
  **LOG estruturado .txt** para download ou cópia, contendo:
  - Data/hora do simulado;
  - Estatísticas gerais (acertos/erros/não respondidas/aproveitamento);
  - Questões erradas no formato:
    `[MATÉRIA] | [TÓPICO] | ID da Questão | Alternativa Marcada | Gabarito Correto`.

### Utilitário de questões (parser_helper.py)

Modo gráfico (Streamlit):

```bash
streamlit run parser_helper.py
```

Modo terminal (CLI):

```bash
python parser_helper.py --listar                                # resumo do banco
python parser_helper.py --interativo                            # cadastrar 1 questão
python parser_helper.py --converter entrada.json                # converter JSON/lista Python bruto
python parser_helper.py --converter entrada.txt --substituir    # substitui todo o banco
python parser_helper.py --json '[{"materia":"X","topico":"Y","enunciado":"Z","alternativas":["a","b"],"gabarito":"A"}]'
```

O conversor aceita variações comuns: chaves em inglês (`subject/topic/question/alternatives/answer`),
alternativas como lista `["op A", "op B", ...]` e gabarito numérico ou em texto ("letra B", "d)").

## Formato do `questoes.json`

```json
[
  {
    "id": 1,
    "materia": "Língua Portuguesa",
    "topico": "Compreensão e Interpretação de Texto",
    "enunciado": "Texto do enunciado aqui...",
    "alternativas": {"A": "Opção A", "B": "Opção B", "C": "Opção C", "D": "Opção D"},
    "gabarito": "B"
  }
]
```

## Exemplo de log gerado

```text
==============================================================
LOG DE SIMULADO - CONCURSO PÚBLICO
==============================================================
Data/Hora de início : 15/10/2026 08:00:00
Data/Hora de término: 15/10/2026 08:35:12
Duração             : 35min 12s
Modo                : Simulado Completo (50 questões)
Total de questões   : 50
--------------------------------------------------------------
ESTATÍSTICAS GERAIS
  Acertos         : 32
  Erros           : 15
  Não respondidas : 3
  Aproveitamento  : 64.0%
--------------------------------------------------------------
DESEMPENHO POR MATÉRIA
  Língua Portuguesa             : 7/12 (58.3%)
  Matemática                    : 9/13 (69.2%)
--------------------------------------------------------------
QUESTÕES ERRADAS
[MATÉRIA] | [TÓPICO] | ID | Marcada | Gabarito
  [Matemática] | [Porcentagem] | ID 36 | Marcada: B | Gabarito: A
==============================================================
FIM DO LOG
```
