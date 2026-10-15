# -*- coding: utf-8 -*-
"""
parser_helper.py - Utilitário de conversão/inclusão de questões
================================================================

Permite preparar e inserir questões no formato esperado pelo app.py
(questoes.json) de três maneiras:

1. MODO CLI INTERATIVO   : python parser_helper.py --interativo
2. MODO CLI (ARGUMENTOS) : python parser_helper.py --adicionar ...
3. CONVERSÃO DE ARQUIVO  : python parser_helper.py --converter entrada.json [-s]
4. MODO STREAMLIT        : streamlit run parser_helper.py

O script detecta automaticamente se está sendo executado dentro do
Streamlit; nesse caso, apresenta uma interface gráfica lateral simples.

Formato canônico de uma questão:
{
  "id": 1,
  "materia": "Língua Portuguesa",
  "topico": "Compreensão e Interpretação de Texto",
  "enunciado": "...",
  "alternativas": {"A": "...", "B": "...", "C": "...", "D": "..."},
  "gabarito": "B"
}
"""

import argparse       # Parsing dos argumentos de linha de comando
import ast            # Avaliação segura de listas de dicionários em Python
import json           # Leitura/escrita do banco de questões
import os             # Operações em arquivos
import sys            # Detecção de ambiente (CLI x Streamlit)

ARQUIVO_PADRAO = "questoes.json"  # Banco de questões usado pelo app.py


# ---------------------------------------------------------------------------
# VALIDAÇÃO E NORMALIZAÇÃO
# ---------------------------------------------------------------------------
def normalizar_questao(bruta: dict, proximo_id: int) -> dict:
    """
    Converte um dicionário 'bruto' para o formato canônico da aplicação.

    Tolerâncias aceitas (conversão "de qualquer lista para o padrão"):
      - chaves em inglês: subject/topic/question/alternatives/answer
      - alternativas como LISTA de textos ["op A", "op B", ...] => vira A/B/C/D/E
      - gabarito como número da opção (0-based ou 1-based) ou letra minúscula
      - campo 'id' ausente => recebe o próximo id disponível

    Lança ValueError se a questão não puder ser normalizada.
    """
    if not isinstance(bruta, dict):
        raise ValueError("A questão deve ser um dicionário.")

    mapa_chaves = {  # apelidos aceitos -> chave canônica
        "materia": "materia", "subject": "materia", "disciplina": "materia",
        "topico": "topico", "topic": "topico", "assunto": "topico",
        "enunciado": "enunciado", "question": "enunciado", "texto": "enunciado",
        "alternativas": "alternativas", "alternatives": "alternativas",
        "opcoes": "alternativas", "options": "alternativas",
        "gabarito": "gabarito", "answer": "gabarito", "resposta": "gabarito",
        "correct": "gabarito",
    }

    minusculas = {str(k).lower(): v for k, v in bruta.items()}

    def obter(*nomes: str):
        """
        Busca o primeiro nome de chave existente, aceitando tanto a grafia
        canônica em português quanto apelidos em inglês (case-insensitive).
        Ex.: 'materia' OU 'subject'; 'gabarito' OU 'answer'.
        """
        for nome in nomes:
            alvo = mapa_chaves.get(nome, nome).lower()
            # 1) procura exata pela grafia canônica
            if alvo in minusculas:
                return minusculas[alvo]
            # 2) procura pelos sinônimos que apontam para a mesma chave canônica
            for apelido, canonica in mapa_chaves.items():
                if canonica == alvo and apelido in minusculas:
                    return minusculas[apelido]
        return None

    materia = obter("materia")
    topico = obter("topico")
    enunciado = obter("enunciado")
    alternativas_brutas = obter("alternativas")
    gabarito_bruto = obter("gabarito")

    # ---- validação dos campos obrigatórios -------------------------------
    faltando = [nome for nome, valor in
                [("materia", materia), ("topico", topico),
                 ("enunciado", enunciado), ("alternativas", alternativas_brutas),
                 ("gabarito", gabarito_bruto)]
                if valor is None or (isinstance(valor, str) and not valor.strip())]
    if faltando:
        raise ValueError(f"Campos ausentes: {', '.join(faltando)}")

    # ---- normalização das alternativas ------------------------------------
    letras = "ABCDE"
    alternativas: dict[str, str] = {}
    indice_correto_de_lista = None  # usado quando o gabarito é numérico

    if isinstance(alternativas_brutas, list):
        if len(alternativas_brutas) < 2 or len(alternativas_brutas) > 5:
            raise ValueError("A lista de alternativas deve ter de 2 a 5 itens.")
        for i, texto in enumerate(alternativas_brutas):
            alternativas[letras[i]] = str(texto).strip()
    elif isinstance(alternativas_brutas, dict):
        for letra, texto in alternativas_brutas.items():
            chave = str(letra).strip().upper().rstrip(")")
            if chave in letras:
                alternativas[chave] = str(texto).strip()
        if len(alternativas) < 2:
            raise ValueError("São necessárias ao menos 2 alternativas (A..E).")
    else:
        raise ValueError("Alternativas devem ser uma lista ou um dicionário.")

    # ---- normalização do gabarito -----------------------------------------
    gabarito: str | None = None
    if isinstance(gabarito_bruto, (int, float)):
        # Número: aceita 0-based (0..4) e 1-based (1..5)
        numero = int(gabarito_bruto)
        if isinstance(alternativas_brutas, list):
            if 0 <= numero < len(alternativas_brutas):
                gabarito = letras[numero]              # 0-based
            elif 1 <= numero <= len(alternativas_brutas):
                gabarito = letras[numero - 1]          # 1-based
        else:
            if 0 <= numero < len(alternativas):
                gabarito = letras[numero]
            elif 1 <= numero <= len(alternativas):
                gabarito = letras[numero - 1]
    else:
        texto = str(gabarito_bruto).strip().upper()
        # 1) Correspondência direta: "B", "b)", "B." etc.
        for letra in letras:
            if texto == letra or texto.rstrip(").: ") == letra:
                gabarito = letra
                break
        # 2) Expressões compostas: "LETRA A", "OPCAO C", "RESPOSTA D"...
        if gabarito is None:
            palavras = texto.replace(")", " ").replace(".", " ").split()
            candidatos = [p for p in palavras if p in letras]
            if candidatos:
                gabarito = candidatos[-1]
        # 3) Última tentativa: casar pelo texto completo da alternativa
        if gabarito is None:
            for letra, conteudo in alternativas.items():
                if conteudo.upper() == texto:
                    gabarito = letra
                    break

    if gabarito is None or gabarito not in alternativas:
        raise ValueError(
            f"Gabarito inválido: '{gabarito_bruto}'. Use uma letra "
            f"existente ({'/'.join(alternativas.keys())})."
        )

    # ---- montagem final ------------------------------------------------------
    id_bruto = bruta.get("id")
    try:
        identificador = int(id_bruto) if id_bruto is not None else proximo_id
    except (TypeError, ValueError):
        identificador = proximo_id

    return {
        "id": identificador,
        "materia": str(materia).strip(),
        "topico": str(topico).strip(),
        "enunciado": str(enunciado).strip(),
        "alternativas": {l: alternativas[l] for l in letras if l in alternativas},
        "gabarito": gabarito,
    }


# ---------------------------------------------------------------------------
# OPERAÇÕES SOBRE O BANCO DE QUESTÕES
# ---------------------------------------------------------------------------
def carregar_banco(caminho: str) -> list[dict]:
    """Lê o banco de questões; retorna lista vazia se o arquivo não existir."""
    if not os.path.exists(caminho):
        return []
    try:
        with open(caminho, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        return dados if isinstance(dados, list) else []
    except (json.JSONDecodeError, OSError) as erro:
        print(f"[ERRO] Falha ao ler '{caminho}': {erro}")
        return []


def salvar_banco(banco: list[dict], caminho: str) -> None:
    """Grava o banco de questões em JSON formatado (UTF-8, indentado)."""
    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump(banco, arquivo, ensure_ascii=False, indent=2)


def proximo_identificador(banco: list[dict]) -> int:
    """Calcula o próximo ID livre (maior id atual + 1)."""
    ids = [q.get("id", 0) for q in banco if isinstance(q, dict)]
    ids = [i for i in ids if isinstance(i, int)]
    return (max(ids) + 1) if ids else 1


def adicionar_questoes(novas_brutas: list[dict], caminho: str,
                      substituir: bool = False) -> tuple[int, list[str]]:
    """
    Normaliza e insere questões no banco.

    Parâmetros:
        novas_brutas : lista de dicionários no formato livre (bruto).
        caminho      : arquivo JSON de destino.
        substituir   : True para SUBSTITUIR todo o banco; False para ACRESCENTAR.

    Retorna (quantidade_inserida, lista_de_erros).
    """
    banco = [] if substituir else carregar_banco(caminho)
    erros: list[str] = []
    inseridas = 0
    base_id = proximo_identificador(banco)

    for indice, bruta in enumerate(novas_brutas, start=1):
        try:
            # Se substituir, força renumeração; senão mantém id próprio ou novo
            questao = normalizar_questao(bruta, proximo_id=base_id + inseridas)
            if substituir:
                questao["id"] = indice  # renumera 1..N no modo substituição
            # Evita IDs duplicados no modo acréscimo
            if any(q.get("id") == questao["id"] for q in banco):
                questao["id"] = proximo_identificador(banco)
            banco.append(questao)
            inseridas += 1
        except ValueError as erro:
            erros.append(f"Questão nº {indice}: {erro}")

    if inseridas > 0:
        salvar_banco(banco, caminho)

    return inseridas, erros


# ---------------------------------------------------------------------------
# CONVERSÃO DE ARQUIVOS (JSON bruto / lista Python) -> questoes.json
# ---------------------------------------------------------------------------
def ler_arquivo_entrada(caminho: str) -> list[dict]:
    """
    Lê um arquivo de entrada que pode ser:
      - JSON contendo uma lista de dicionários; OU
      - Python literal (lista de dicts escrita em sintaxe Python, ex.: [{...}]).
    """
    with open(caminho, "r", encoding="utf-8") as arquivo:
        conteudo = arquivo.read().strip()

    # Tenta JSON primeiro (formato mais comum)
    try:
        dados = json.loads(conteudo)
    except json.JSONDecodeError:
        # Tenta interpretar como literal Python: [ {...}, {...} ]
        try:
            dados = ast.literal_eval(conteudo)
        except (ValueError, SyntaxError) as erro:
            raise ValueError(
                f"Não foi possível interpretar '{caminho}' nem como JSON "
                f"nem como lista Python. Detalhes: {erro}"
            )

    if isinstance(dados, dict):
        dados = [dados]  # aceita arquivo com uma única questão
    if not isinstance(dados, list):
        raise ValueError("A entrada deve ser uma lista de questões.")
    return dados


# ---------------------------------------------------------------------------
# INTERFACE CLI INTERATIVA (modo pergunta-resposta no terminal)
# ---------------------------------------------------------------------------
def cli_interativo(caminho: str) -> None:
    """Percorre um assistente de terminal para cadastrar uma nova questão."""
    print("=" * 60)
    print("CADASTRO INTERATIVO DE QUESTÃO")
    print(f"Banco de destino: {caminho}")
    print("=" * 60)

    banco = carregar_banco(caminho)
    print(f"Questões atuais no banco: {len(banco)}\n")

    materia = input("Matéria (ex.: Língua Portuguesa): ").strip()
    topico = input("Tópico (ex.: Concordância Verbal): ").strip()
    print("Enunciado (digite e pressione Enter duas vezes para terminar):")
    linhas = []
    while True:
        linha = input()
        if linha == "":
            break
        linhas.append(linha)
    enunciado = "\n".join(linhas).strip()

    alternativas: dict[str, str] = {}
    for letra in "ABCDE":
        texto = input(f"Alternativa {letra} (Enter para parar em D/E): ").strip()
        if not texto and letra >= "D":
            break
        alternativas[letra] = texto
    if len(alternativas) < 2:
        print("[ERRO] Informe ao menos 2 alternativas. Nada foi salvo.")
        return

    gabarito = input("Gabarito correto (letra): ").strip().upper()

    nova = {
        "materia": materia,
        "topico": topico,
        "enunciado": enunciado,
        "alternativas": alternativas,
        "gabarito": gabarito,
    }
    inseridas, erros = adicionar_questoes([nova], caminho)
    if inseridas:
        print(f"\n✅ Questão salva com sucesso em '{caminho}'.")
    for erro in erros:
        print(f"❌ {erro}")


# ---------------------------------------------------------------------------
# INTERFACE STREAMLIT (executado via: streamlit run parser_helper.py)
# ---------------------------------------------------------------------------
def interface_streamlit() -> None:
    """Interface gráfica para inserir/converter questões sem usar o terminal."""
    import streamlit as st  # import tardio: só carregado dentro do Streamlit

    st.set_page_config(page_title="Parser Helper - Questões", page_icon="🧩")
    st.title("🧩 Parser Helper — Inclusão e Conversão de Questões")

    caminho = st.text_input("Arquivo de destino", value=ARQUIVO_PADRAO)

    aba_manual, aba_conversao = st.tabs(
        ["✍️ Inserir questão", "🔄 Converter JSON / lista Python"]
    )

    # ---- Aba 1: formulário manual ---------------------------------------
    with aba_manual:
        materia = st.text_input("Matéria*", placeholder="Língua Portuguesa")
        topico = st.text_input("Tópico*", placeholder="Compreensão de Texto")
        enunciado = st.text_area("Enunciado*")
        st.markdown("**Alternativas** (deixe as últimas vazias para omiti-las):")
        cols = st.columns(5)
        textos = [
            cols[i].text_input(f"Alternativa {letra}", key=f"alt_{letra}")
            for i, letra in enumerate("ABCDE")
        ]
        gabarito = st.selectbox("Gabarito*", list("ABCDE"))
        substituir = st.checkbox(
            "Substituir TODO o banco por esta questão (padrão: acrescentar)"
        )

        if st.button("💾 Salvar questão", type="primary"):
            alternativas = {
                letra: texto.strip()
                for letra, texto in zip("ABCDE", textos) if texto.strip()
            }
            if not (materia and topico and enunciado.strip() and alternativas):
                st.error("Preencha matéria, tópico, enunciado e alternativas.")
            elif gabarito not in alternativas:
                st.error(f"A alternativa {gabarito} está vazia mas foi marcada "
                         "como gabarito.")
            else:
                bruta = {
                    "materia": materia, "topico": topico,
                    "enunciado": enunciado, "alternativas": alternativas,
                    "gabarito": gabarito,
                }
                inseridas, erros = adicionar_questoes([bruta], caminho,
                                                      substituir=substituir)
                if inseridas:
                    st.success(f"Questão salva em '{caminho}'!")
                for erro in erros:
                    st.error(erro)

    # ---- Aba 2: conversão em lote ------------------------------------------
    with aba_conversao:
        st.markdown(
            "Cole uma lista de dicionários em **JSON** ou **sintaxe Python** "
            "(aceita chaves em inglês, alternativas como lista e gabarito "
            "numérico) e converta para o padrão da aplicação."
        )
        texto_colado = st.text_area(
            "Conteúdo bruto (JSON ou lista Python):", height=250,
            placeholder='[\n  {"materia": "Matemática", "topico": "Porcentagem",'
                        '\n   "enunciado": "...", "alternativas": ["20%", "30%",'
                        ' "40%", "50%"], "gabarito": 1}\n]'
        )
        opcao_substituicao = st.radio(
            "Modo de gravação", ["Acrescentar ao banco", "Substituir o banco"]
        )

        if st.button("🔄 Converter e salvar"):
            if not texto_colado.strip():
                st.error("Cole algum conteúdo antes de converter.")
            else:
                try:
                    dados = json.loads(texto_colado)
                except json.JSONDecodeError:
                    try:
                        dados = ast.literal_eval(texto_colado)
                    except (ValueError, SyntaxError) as erro:
                        st.error(f"Entrada ilegível: {erro}")
                        dados = None
                if dados is not None:
                    if isinstance(dados, dict):
                        dados = [dados]
                    inseridas, erros = adicionar_questoes(
                        dados, caminho,
                        substituir=(opcao_substituicao == "Substituir o banco"),
                    )
                    st.success(f"{inseridas} questão(ões) convertida(s) e "
                               f"salva(s) em '{caminho}'.")
                    for erro in erros:
                        st.warning(erro)

        st.divider()
        upload = st.file_uploader("Ou envie um arquivo .json/.txt/.py",
                                  type=["json", "txt", "py"])
        if upload is not None and st.button("⬆️ Converter arquivo enviado"):
            try:
                conteudo = upload.getvalue().decode("utf-8")
                import tempfile
                with tempfile.NamedTemporaryFile(
                    "w", suffix=".txt", delete=False, encoding="utf-8"
                ) as temporario:
                    temporario.write(conteudo)
                    caminho_temp = temporario.name
                lista_bruta = ler_arquivo_entrada(caminho_temp)
                os.unlink(caminho_temp)
                inseridas, erros = adicionar_questoes(lista_bruta, caminho)
                st.success(f"{inseridas} questão(ões) importada(s).")
                for erro in erros:
                    st.warning(erro)
            except (ValueError, OSError) as erro:
                st.error(str(erro))

    # ---- Visualização do banco atual ---------------------------------------
    st.divider()
    st.subheader("📦 Banco atual")
    banco = carregar_banco(caminho)
    st.write(f"**{len(banco)} questão(ões)** em `{caminho}`")
    if banco:
        st.json(banco[:5])
        if len(banco) > 5:
            st.caption("(mostrando apenas as 5 primeiras)")


# ---------------------------------------------------------------------------
# DETECÇÃO DE AMBIENTE E ENTRADA PRINCIPAL
# ---------------------------------------------------------------------------
def rodando_no_streamlit() -> bool:
    """
    Detecta se este arquivo está sendo executado pelo Streamlit.

    O Streamlit injeta o módulo 'streamlit.runtime.scriptrunner' com uma
    sessão ativa; também verificamos o argv, pois 'streamlit run' altera
    a linha de comando do processo.
    """
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        if get_script_run_ctx() is not None:
            return True
    except Exception:
        pass
    return any("streamlit" in arg for arg in sys.argv)


def montar_parser() -> argparse.ArgumentParser:
    """Constrói o interpretador de argumentos da CLI."""
    parser = argparse.ArgumentParser(
        prog="parser_helper.py",
        description=(
            "Utilitário para inserir e converter questões para o formato "
            "de questoes.json usado pelo simulado (app.py)."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("-f", "--arquivo", default=ARQUIVO_PADRAO,
                        help="Caminho do banco de questões (padrão: questoes.json)")
    parser.add_argument("-i", "--interativo", action="store_true",
                        help="Assistente interativo no terminal para 1 questão")
    parser.add_argument("-c", "--converter", metavar="ENTRADA",
                        help="Converte um arquivo JSON/lista Python para o padrão")
    parser.add_argument("--adicionar", nargs="+", metavar="ID_DO_JSON",
                        help=(
                            "Seleciona questões pela chave 'id' de um arquivo\n"
                            "de entrada (use junto com --converter-candidato)\n"
                            "ou cole JSON inline com --json"
                        ))
    parser.add_argument("--json", metavar="STRING_JSON",
                        help="Insere uma lista de questões JSON direto na linha\n"
                             "de comando. Ex.: --json '[{\"materia\": ...}]'")
    parser.add_argument("-s", "--substituir", action="store_true",
                        help="Substitui todo o banco em vez de acrescentar")
    parser.add_argument("--listar", action="store_true",
                        help="Mostra um resumo do banco atual e sai")
    return parser


def main_cli(argv: list[str]) -> int:
    """Executa a lógica da linha de comando. Retorna o código de saída."""
    parser = montar_parser()
    args = parser.parse_args(argv)
    caminho = args.arquivo

    # --listar : resumo rápido do banco
    if args.listar:
        banco = carregar_banco(caminho)
        print(f"Banco: {caminho} | Questões: {len(banco)}")
        materias: dict[str, int] = {}
        for questao in banco:
            if isinstance(questao, dict):
                materias[questao.get("materia", "?")] = \
                    materias.get(questao.get("materia", "?"), 0) + 1
        for materia, quantidade in sorted(materias.items()):
            print(f"  - {materia}: {quantidade}")
        return 0

    # --interativo : assistente de cadastro
    if args.interativo:
        cli_interativo(caminho)
        return 0

    # --converter : importa arquivo bruto (JSON ou lista Python)
    if args.converter:
        try:
            lista_bruta = ler_arquivo_entrada(args.converter)
        except (ValueError, OSError) as erro:
            print(f"[ERRO] {erro}")
            return 1
        # Filtro opcional por IDs específicos: --adicionar 1 4 7
        if args.adicionar:
            desejados = {int(x) for x in args.adicionar}
            lista_bruta = [q for q in lista_bruta
                           if isinstance(q, dict) and q.get("id") in desejados]
        inseridas, erros = adicionar_questoes(lista_bruta, caminho,
                                              substituir=args.substituir)
        print(f"✅ {inseridas} questão(ões) gravada(s) em '{caminho}'.")
        for erro in erros:
            print(f"❌ {erro}")
        return 0 if not erros else 2

    # --json : inserção direta de uma lista JSON na linha de comando
    if args.json:
        try:
            lista_bruta = json.loads(args.json)
        except json.JSONDecodeError as erro:
            print(f"[ERRO] JSON inválido em --json: {erro}")
            return 1
        if isinstance(lista_bruta, dict):
            lista_bruta = [lista_bruta]
        inseridas, erros = adicionar_questoes(lista_bruta, caminho,
                                              substituir=args.substituir)
        print(f"✅ {inseridas} questão(ões) gravada(s) em '{caminho}'.")
        for erro in erros:
            print(f"❌ {erro}")
        return 0 if not erros else 2

    parser.print_help()
    return 0


if __name__ == "__main__":
    # Roteamento automático: Streamlit (via 'streamlit run') ou CLI pura
    if rodando_no_streamlit():
        interface_streamlit()
    else:
        sys.exit(main_cli(sys.argv[1:]))
