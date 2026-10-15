# -*- coding: utf-8 -*-
"""
app.py - Aplicação Streamlit de Simulados para Concurso Público
================================================================

Foco: análise de desempenho orientada a dados.

Fluxo principal:
1. Carrega o banco de questões local (questoes.json).
2. Permite configurar o simulado (modo e filtro de matérias).
3. Exibe a prova com cronômetro e barra de progresso.
4. Ao finalizar, calcula estatísticas gerais e por matéria e
   gera um LOG estruturado em .txt para download/cópia.

Execução:
    streamlit run app.py
"""

import json          # Leitura/escrita do banco de questões e do log
import os            # Verificação de existência de arquivos
import random        # Sorteio das questões
from datetime import datetime  # Data/hora do simulado e controle do tempo

import streamlit as st  # Framework da interface web


# ---------------------------------------------------------------------------
# CONSTANTES DE CONFIGURAÇÃO
# ---------------------------------------------------------------------------
ARQUIVO_QUESTOES = "questoes.json"   # Banco de questões local
QTD_TREINO_LIVRE = 20                # Questões no modo "Treino Livre"
QTD_SIMULADO_COMPLETO = 50           # Questões no modo "Simulado Completo"

# Cores/estilos usados na apresentação dos resultados
ESTILO_CERTO = "🟢"
ESTILO_ERRADO = "🔴"


# ---------------------------------------------------------------------------
# BANCO DE QUESTÕES DE EXEMPLO (criado automaticamente se não houver arquivo)
# ---------------------------------------------------------------------------
def questoes_exemplo() -> list[dict]:
    """
    Retorna uma lista mínima de questões de exemplo.

    Essa função é usada apenas quando o arquivo 'questoes.json'
    ainda não existe, garantindo que a aplicação funcione de imediato.
    """
    return [
        {
            "id": 1,
            "materia": "Língua Portuguesa",
            "topico": "Compreensão e Interpretação de Texto",
            "enunciado": (
                "Leia o trecho: 'A leitura é para quem não sabe escrever; "
                "escrever é para quem já leu demais.' Assinale a alternativa "
                "que melhor resume a ideia central do trecho."
            ),
            "alternativas": {
                "A": "Ler é mais importante do que escrever.",
                "B": "Escrever pressupõe muita leitura prévia.",
                "C": "Quem lê muito perde a capacidade de escrever.",
                "D": "Leitura e escrita são atividades independentes.",
            },
            "gabarito": "B",
        },
        {
            "id": 2,
            "materia": "Língua Portuguesa",
            "topico": "Concordância Verbal",
            "enunciado": (
                "Assinale a frase em que a concordância verbal está correta "
                "de acordo com a norma-padrão."
            ),
            "alternativas": {
                "A": "Fazem dez anos que estudo para concursos.",
                "B": "Houveram muitos candidatos aprovados.",
                "C": "Faz dez anos que estudo para concursos.",
                "D": "Existiam muitas pessoas na fila, ontem.",
            },
            "gabarito": "C",
        },
        {
            "id": 3,
            "materia": "Matemática",
            "topico": "Porcentagem",
            "enunciado": (
                "Um produto custava R$ 200,00 e sofreu um aumento de 15%. "
                "Qual é o novo preço do produto?"
            ),
            "alternativas": {
                "A": "R$ 215,00",
                "B": "R$ 230,00",
                "C": "R$ 225,00",
                "D": "R$ 245,00",
            },
            "gabarito": "B",
        },
        {
            "id": 4,
            "materia": "Matemática",
            "topico": "Raciocínio Lógico",
            "enunciado": (
                "Se todo A é B e nenhum B é C, então é necessariamente "
                "verdadeiro que:"
            ),
            "alternativas": {
                "A": "Algum A é C.",
                "B": "Nenhum A é C.",
                "C": "Todo C é A.",
                "D": "Algum B é A somente se for C.",
            },
            "gabarito": "B",
        },
        {
            "id": 5,
            "materia": "Informática",
            "topico": "Editores de Texto",
            "enunciado": (
                "No Microsoft Word, qual atalho de teclado é usado para "
                "salvar um documento?"
            ),
            "alternativas": {
                "A": "Ctrl + P",
                "B": "Ctrl + V",
                "C": "Ctrl + S",
                "D": "Ctrl + Z",
            },
            "gabarito": "C",
        },
        {
            "id": 6,
            "materia": "Informática",
            "topico": "Segurança da Informação",
            "enunciado": (
                "O golpe eletrônico em que o criminoso se passa por pessoa ou "
                "empresa de confiança para obter dados sensíveis é chamado de:"
            ),
            "alternativas": {
                "A": "Phishing",
                "B": "Backup",
                "C": "Firewall",
                "D": "Cache",
            },
            "gabarito": "A",
        },
        {
            "id": 7,
            "materia": "Direito Constitucional",
            "topico": "Direitos Fundamentais",
            "enunciado": (
                "Segundo a Constituição Federal de 1988, são direitos sociais, "
                "EXCETO:"
            ),
            "alternativas": {
                "A": "Educação.",
                "B": "Saúde.",
                "C": "Liberdade de locomoção.",
                "D": "Trabalho.",
            },
            "gabarito": "C",
        },
        {
            "id": 8,
            "materia": "Direito Constitucional",
            "topico": "Organização do Estado",
            "enunciado": (
                "A República Federativa do Brasil é formada pela união "
                "indissolúvel dos Estados e Municípios e do Distrito Federal e "
                "tem como fundamento:"
            ),
            "alternativas": {
                "A": "A prevalência dos interesses econômicos regionais.",
                "B": "A dignidade da pessoa humana.",
                "C": "A centralização administrativa absoluta.",
                "D": "O sistema parlamentarista de governo.",
            },
            "gabarito": "B",
        },
    ]


# ---------------------------------------------------------------------------
# CARREGAMENTO E VALIDAÇÃO DOS DADOS
# ---------------------------------------------------------------------------
def carregar_questoes(caminho: str = ARQUIVO_QUESTOES) -> list[dict]:
    """
    Lê o arquivo JSON de questões.

    - Se o arquivo não existir, cria um exemplo mínimo automático.
    - Valida a estrutura básica de cada questão, descartando itens inválidos.

    Retorna a lista de questões válidas.
    """
    # Caso 1: arquivo inexistente -> criar exemplo mínimo automático
    if not os.path.exists(caminho):
        exemplos = questoes_exemplo()
        try:
            with open(caminho, "w", encoding="utf-8") as arquivo:
                json.dump(exemplos, arquivo, ensure_ascii=False, indent=2)
            st.toast(f"Arquivo '{caminho}' criado com questões de exemplo.")
            return exemplos
        except OSError as erro:
            st.error(f"Não foi possível criar o arquivo de questões: {erro}")
            return exemplos  # segue funcionando com os exemplos em memória

    # Caso 2: arquivo existente -> ler e validar
    try:
        with open(caminho, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
    except json.JSONDecodeError as erro:
        st.error(
            f"O arquivo '{caminho}' contém JSON inválido. "
            "Corrija-o usando o parser_helper.py. Erro: " + str(erro)
        )
        return []
    except OSError as erro:
        st.error(f"Erro ao ler o arquivo '{caminho}': {erro}")
        return []

    # Garante que o topo do JSON seja uma lista
    if not isinstance(dados, list):
        st.error("Formato inesperado: o JSON raiz deve ser uma lista de questões.")
        return []

    # Validação campo a campo de cada questão
    chaves_obrigatorias = {"id", "materia", "topico", "enunciado",
                           "alternativas", "gabarito"}
    questoes_validas: list[dict] = []
    for indice, questao in enumerate(dados):
        if not isinstance(questao, dict):
            continue
        if not chaves_obrigatorias.issubset(questao.keys()):
            continue
        alternativas = questao.get("alternativas")
        gabarito = questao.get("gabarito")
        # As alternativas devem ser um dicionário A->texto e o gabarito
        # deve apontar para uma letra existente nesse dicionário.
        if not isinstance(alternativas, dict) or not alternativas:
            continue
        if gabarito not in alternativas:
            continue
        questoes_validas.append(questao)

    quantidade_descartada = len(dados) - len(questoes_validas)
    if quantidade_descartada > 0:
        st.warning(
            f"{quantidade_descartada} questão(ões) fora do padrão foram "
            "ignoradas. Use o parser_helper.py para corrigi-las."
        )
    return questoes_validas


# ---------------------------------------------------------------------------
# SELEÇÃO DE QUESTÕES (sorteio simples ou proporcional por matéria)
# ---------------------------------------------------------------------------
def selecionar_questoes(todas: list[dict], quantidade: int,
                        materias_selecionadas: list[str],
                        proporcional: bool) -> list[dict]:
    """
    Sorteia as questões do simulado.

    Parâmetros:
        todas                 : lista completa de questões válidas.
        quantidade            : número desejado de questões.
        materias_selecionadas : lista de matérias filtradas (vazia = todas).
        proporcional          : True para sorteio misto proporcional entre as
                                matérias escolhidas; False para usar apenas as
                                matérias selecionadas (ou todas, se vazio).

    Retorna a lista sorteada de questões (limitada à quantidade disponível).
    """
    pool = list(todas)  # cópia para não alterar a lista original

    if materias_selecionadas:
        pool = [q for q in pool if q["materia"] in materias_selecionadas]

    # Sem seleção de matérias => comportamento natural é proporcional
    if not materias_selecionadas:
        proporcional = True

    if not pool:
        return []

    # Limite prático: nunca sortear mais questões do que existem
    quantidade = min(quantidade, len(pool))

    if not proporcional:
        # Sorteio simples dentro do(s) filtro(s) escolhido(s)
        return random.sample(pool, quantidade)

    # ---- Sorteio MISTO PROPORCIONAL ------------------------------------
    # Divide as questões por matéria e distribui as vagas de forma
    # proporcional ao tamanho de cada matéria, ajustando arredondamentos.
    por_materia: dict[str, list[dict]] = {}
    for questao in pool:
        por_materia.setdefault(questao["materia"], []).append(questao)

    total_pool = len(pool)
    cotas: dict[str, int] = {}
    for materia, lista in por_materia.items():
        cotas[materia] = int(quantidade * len(lista) / total_pool)

    # Distribui as vagas restantes (efeito do arredondamento) nas matérias
    # com maior fração proporcional ainda não preenchida.
    restantes = quantidade - sum(cotas.values())
    ordem_ajuste = sorted(
        por_materia.keys(),
        key=lambda m: len(por_materia[m]) / total_pool - cotas[m] / quantidade
        if quantidade else 0,
        reverse=True,
    )
    for materia in ordem_ajuste:
        if restantes <= 0:
            break
        if len(por_materia[materia]) > cotas[materia]:
            cotas[materia] += 1
            restantes -= 1

    # Aplica as cotas respeitando a disponibilidade real de cada matéria
    sorteio: list[dict] = []
    sobra_global = 0
    for materia, cota in cotas.items():
        disponiveis = por_materia[materia]
        escolher = min(cota, len(disponiveis))
        sorteio.extend(random.sample(disponiveis, escolher))
        sobra_global += cota - escolher

    # Se alguma matéria não pôde preencher a cota, completa com as demais
    if sobra_global > 0:
        ja_selecionadas = {q["id"] for q in sorteio}
        extras = [q for q in pool if q["id"] not in ja_selecionadas]
        if extras:
            sorteio.extend(random.sample(extras, min(sobra_global, len(extras))))

    random.shuffle(sorteio)  # embaralha a ordem final das questões
    return sorteio[:quantidade]


# ---------------------------------------------------------------------------
# GERAÇÃO DO LOG ESTRUTURADO (.txt)
# ---------------------------------------------------------------------------
def gerar_log(inicio: datetime, fim: datetime, questoes: list[dict],
              respostas: dict[int, str], modo: str) -> str:
    """
    Monta o texto do LOG estruturado do simulado.

    Formato exigido:
      - Data e hora do simulado.
      - Estatísticas gerais (Acertos/Erros/Porcentagem).
      - Percentual de acertos POR MATÉRIA.
      - Lista detalhada das questões ERRADAS:
        [MATÉRIA] | [TÓPICO] | ID da Questão | Alternativa Marcada | Gabarito.
    """
    duracao_segundos = int((fim - inicio).total_seconds())
    minutos, segundos = divmod(duracao_segundos, 60)

    acertos = erros = nao_respondidas = 0
    erradas: list[str] = []
    # Contadores por matéria: {matéria: [acertos, totais]}
    estatisticas_materia: dict[str, list[int]] = {}

    for questao in questoes:
        materia = questao["materia"]
        estatisticas_materia.setdefault(materia, [0, 0])
        estatisticas_materia[materia][1] += 1

        resposta = respostas.get(questao["id"])
        if resposta is None:
            nao_respondidas += 1
        elif resposta == questao["gabarito"]:
            acertos += 1
            estatisticas_materia[materia][0] += 1
        else:
            erros += 1
            erradas.append(
                f"[{materia}] | [{questao['topico']}] | "
                f"ID {questao['id']} | "
                f"Marcada: {resposta} | Gabarito: {questao['gabarito']}"
            )

    total = len(questoes)
    porcentagem = (acertos / total * 100) if total else 0.0

    # Cabeçalho do log
    linhas = [
        "=" * 62,
        "LOG DE SIMULADO - CONCURSO PÚBLICO",
        "=" * 62,
        f"Data/Hora de início : {inicio.strftime('%d/%m/%Y %H:%M:%S')}",
        f"Data/Hora de término: {fim.strftime('%d/%m/%Y %H:%M:%S')}",
        f"Duração             : {minutos}min {segundos}s",
        f"Modo                : {modo}",
        f"Total de questões   : {total}",
        "-" * 62,
        "ESTATÍSTICAS GERAIS",
        f"  Acertos         : {acertos}",
        f"  Erros           : {erros}",
        f"  Não respondidas : {nao_respondidas}",
        f"  Aproveitamento  : {porcentagem:.1f}%",
        "-" * 62,
        "DESEMPENHO POR MATÉRIA",
    ]

    # Percentual de acertos por matéria (ordenado alfabeticamente)
    for materia in sorted(estatisticas_materia):
        ac, tot = estatisticas_materia[materia]
        pct = (ac / tot * 100) if tot else 0.0
        linhas.append(f"  {materia:<30}: {ac}/{tot} ({pct:.1f}%)")

    # Detalhamento das questões erradas
    linhas += ["-" * 62, "QUESTÕES ERRADAS",
               "[MATÉRIA] | [TÓPICO] | ID | Marcada | Gabarito"]
    if erradas:
        linhas += [f"  {linha}" for linha in erradas]
    else:
        linhas.append("  Nenhuma questão errada. Parabéns!")

    linhas += ["=" * 62, "FIM DO LOG"]
    return "\n".join(linhas)


# ---------------------------------------------------------------------------
# INTERFACE - PÁGINA INICIAL / CONFIGURAÇÃO
# ---------------------------------------------------------------------------
def pagina_configuracao(questoes: list[dict]) -> None:
    """Exibe a tela de configuração e inicia o simulado."""
    st.title("🎯 Simulados para Concurso Público")
    st.caption(
        "Análise de desempenho orientada a dados — responda, finalize e "
        "exporte seu log estruturado para acompanhar sua evolução."
    )

    st.sidebar.header("⚙️ Configuração")

    # ---------------- Modo do simulado ----------------
    modo = st.sidebar.radio(
        "Modo do simulado",
        options=[
            f"Treino Livre ({QTD_TREINO_LIVRE} questões)",
            f"Simulado Completo ({QTD_SIMULADO_COMPLETO} questões)",
        ],
    )
    quantidade = QTD_TREINO_LIVRE if "Treino" in modo else QTD_SIMULADO_COMPLETO

    # ---------------- Filtro de matérias ----------------
    materias_disponiveis = sorted({q["materia"] for q in questoes})
    st.sidebar.subheader("📚 Matérias")
    materias_selecionadas = st.sidebar.multiselect(
        "Filtrar por matérias (vazio = sorteio misto proporcional)",
        options=materias_disponiveis,
        help="Deixe vazio para um sorteio misto proporcional entre todas "
             "as matérias do banco.",
    )

    # Resumo estatístico do banco de questões (visão orientada a dados)
    st.subheader("📦 Banco de questões")
    colunas = st.columns(max(len(materias_disponiveis), 1))
    for coluna, materia in zip(colunas, materias_disponiveis):
        qtde = sum(1 for q in questoes if q["materia"] == materia)
        coluna.metric(label=materia, value=f"{qtde} questões")

    st.write(
        f"**Disponibilidade atual:** {len(questoes)} questões válidas no banco. "
        f"O simulado solicitará **{quantidade}** questões "
        f"({'sorteio proporcional entre todas as matérias' if not materias_selecionadas else ', '.join(materias_selecionadas)})."
    )

    # ---------------- Botão de início ----------------
    if st.button("🚀 Iniciar Simulado", type="primary"):
        pool_filtrado = [
            q for q in questoes
            if not materias_selecionadas or q["materia"] in materias_selecionadas
        ]
        if not pool_filtrado:
            st.warning("Nenhuma questão disponível para os filtros escolhidos.")
            return

        sorteio = selecionar_questoes(
            todas=questoes,
            quantidade=quantidade,
            materias_selecionadas=materias_selecionadas,
            proporcional=not materias_selecionadas,
        )
        # Salva o estado da prova na sessão do Streamlit
        st.session_state.prova = {
            "questoes": sorteio,
            "modo": modo,
            "inicio": datetime.now(),
            "indice": 0,
            "respostas": {},
        }
        st.rerun()


# ---------------------------------------------------------------------------
# INTERFACE - PROVA
# ---------------------------------------------------------------------------
def pagina_prova() -> None:
    """Exibe uma questão por vez, com cronômetro e barra de progresso."""
    prova = st.session_state.prova
    questoes: list[dict] = prova["questoes"]
    indice: int = prova["indice"]
    total = len(questoes)

    questao = questoes[indice]
    letras = list(questao["alternativas"].keys())

    # ---------------- Cronômetro e progresso ----------------
    decorrido = int((datetime.now() - prova["inicio"]).total_seconds())
    minutos, segundos = divmod(decorrido, 60)
    horas, minutos = divmod(minutos, 60)

    cabecalho = st.columns([2, 2, 3])
    cabecalho[0].metric("Questão", f"{indice + 1} / {total}")
    cabecalho[1].metric("⏱️ Tempo decorrido", f"{horas:02d}:{minutos:02d}:{segundos:02d}")
    respondidas = len(prova["respostas"])
    cabecalho[2].progress(respondidas / total,
                          text=f"Progresso: {respondidas}/{total} respondidas")

    st.progress((indice + 1) / total,
                text=f"Avanço na prova: questão {indice + 1} de {total}")

    # ---------------- Enunciado e alternativas ----------------
    st.subheader(f"📖 Questão {indice + 1}")
    st.markdown(f"*Matéria:* **{questao['materia']}** — *Tópico:* {questao['topico']}")
    st.markdown(f"**Enunciado:**\n\n{questao['enunciado']}")

    nome_campo = f"resposta_{questao['id']}"  # chave única por questão
    resposta_atual = prova["respostas"].get(questao["id"])

    # Radio group para marcar a alternativa (A, B, C, D ou E)
    marcacao = st.radio(
        "Marque a alternativa:",
        options=letras,
        index=letras.index(resposta_atual) if resposta_atual in letras else None,
        format_func=lambda letra: f"{letra}) {questao['alternativas'][letra]}",
        key=nome_campo,
    )
    if marcacao:
        prova["respostas"][questao["id"]] = marcacao

    st.divider()

    # ---------------- Navegação ----------------
    botoes = st.columns([1, 1, 1, 2])

    if botoes[0].button("⬅️ Anterior", disabled=(indice == 0)):
        prova["indice"] -= 1
        st.rerun()

    if botoes[1].button("Próxima ➡️", disabled=(indice == total - 1)):
        prova["indice"] += 1
        st.rerun()

    if botoes[2].button("🔄 Recomeçar"):
        if st.session_state.pop("prova", None) is not None:
            st.rerun()

    # Botão de finalização (destaque)
    if botoes[3].button("✅ FINALIZAR SIMULADO", type="primary"):
        sem_resposta = total - len(prova["respostas"])
        if sem_resposta > 0 and not prova.get("confirmado", False):
            prova["confirmado"] = True
            st.warning(
                f"Há {sem_resposta} questão(ões) sem resposta. "
                "Clique novamente em FINALIZAR para confirmar."
            )
        else:
            prova["fim"] = datetime.now()
            st.rerun()


# ---------------------------------------------------------------------------
# INTERFACE - RESULTADOS
# ---------------------------------------------------------------------------
def pagina_resultados() -> None:
    """Mostra o boletim de desempenho e disponibiliza o log .txt."""
    prova = st.session_state.prova
    questoes: list[dict] = prova["questoes"]
    respostas: dict[int, str] = prova["respostas"]
    inicio: datetime = prova["inicio"]
    fim: datetime = prova.get("fim", datetime.now())

    # ---------------- Estatísticas gerais ----------------
    acertos = sum(
        1 for q in questoes if respostas.get(q["id"]) == q["gabarito"]
    )
    total = len(questoes)
    erros = sum(1 for q in questoes
                if q["id"] in respostas and respostas[q["id"]] != q["gabarito"])
    nao_respondidas = total - acertos - erros
    porcentagem = (acertos / total * 100) if total else 0.0

    st.title("🏁 Resultado do Simulado")
    cols = st.columns(4)
    cols[0].metric("Acertos", acertos)
    cols[1].metric("Erros", erros)
    cols[2].metric("Não respondidas", nao_respondidas)
    cols[3].metric("Aproveitamento", f"{porcentagem:.1f}%")

    # ---------------- Desempenho por matéria ----------------
    st.subheader("📊 Acertos por matéria")
    materias = sorted({q["materia"] for q in questoes})
    dados_materias = []
    for materia in materias:
        do_tema = [q for q in questoes if q["materia"] == materia]
        acertadas = sum(1 for q in do_tema
                        if respostas.get(q["id"]) == q["gabarito"])
        pct = (acertadas / len(do_tema) * 100) if do_tema else 0.0
        dados_materias.append((materia, acertadas, len(do_tema), pct))
        st.write(f"**{materia}**: {acertadas}/{len(do_tema)} — {pct:.1f}%")
        st.progress(pct / 100)

    # ---------------- Revisão detalhada ----------------
    st.subheader("🔍 Revisão das questões")
    for numero, questao in enumerate(questoes, start=1):
        resposta = respostas.get(questao["id"])
        acertou = resposta == questao["gabarito"]
        simbolo = ESTILO_CERTO if acertou else ESTILO_ERRADO
        rotulo = (
            f"{simbolo} Q{numero} — {questao['materia']} "
            f"(sua resposta: {resposta or '—'} | gabarito: {questao['gabarito']})"
        )
        with st.expander(rotulo):
            st.markdown(questao["enunciado"])
            for letra, texto in questao["alternativas"].items():
                marcador = ""
                if letra == questao["gabarito"]:
                    marcador = " ✅ **(gabarito)**"
                elif letra == resposta:
                    marcador = " ❌ *(sua resposta)*"
                st.markdown(f"- **{letra})** {texto}{marcador}")

    # ---------------- Log estruturado (.txt) ----------------
    st.subheader("📄 Log estruturado")
    log_texto = gerar_log(inicio, fim, questoes, respostas, prova["modo"])

    nome_arquivo = (
        f"simulado_{inicio.strftime('%Y%m%d_%H%M%S')}.txt"
    )

    col_download, col_area = st.columns([1, 2])
    with col_download:
        st.download_button(
            label="⬇️ Baixar LOG (.txt)",
            data=log_texto.encode("utf-8"),
            file_name=nome_arquivo,
            mime="text/plain",
        )
    with col_area:
        # Área de texto selecionável facilita copiar o conteúdo manualmente
        st.text_area("Conteúdo do log (selecione e copie com Ctrl+C):",
                     log_texto, height=300)

    st.code(log_texto, language="text")  # versão monoespaçada para conferência

    if st.button("🏠 Voltar à configuração", type="primary"):
        st.session_state.pop("prova", None)
        st.rerun()


# ---------------------------------------------------------------------------
# PONTO DE ENTRADA DA APLICAÇÃO
# ---------------------------------------------------------------------------
def main() -> None:
    """Roteia entre as páginas conforme o estado da sessão."""
    st.set_page_config(
        page_title="Simulados Concurso Público",
        page_icon="🎯",
        layout="wide",
    )

    # Carrega (ou cria) o banco de questões a cada execução do script
    questoes = carregar_questoes()

    prova = st.session_state.get("prova")
    if prova is None:
        pagina_configuracao(questoes)
    elif "fim" in prova:
        pagina_resultados()
    else:
        if not prova["questoes"]:
            st.error("Não foi possível montar a prova. Volte e tente novamente.")
            st.session_state.pop("prova", None)
            st.rerun()
        pagina_prova()


if __name__ == "__main__":
    main()
