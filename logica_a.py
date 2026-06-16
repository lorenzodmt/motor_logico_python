import streamlit as st
import pandas as pd
import itertools
import re

class MotorLogico:
    def __init__(self):
        self.REPLACEMENTS = [
            ('<->', '=='),
            ('->', ' <= '),
            ('&', ' and '),
            ('|', ' or ')
        ]

    def normalizar_expressao(self, expressao: str) -> str:
        """Converte variáveis para maiúsculas, padroniza conectivos e remove espaços sem usar while."""
        expr = expressao.strip()
        
        # Substituições lineares com Regex (sem loops while que causam travamentos)
        expr = re.sub(r'(\((?:[^()]*)\))\'', r'~\1', expr)
        expr = re.sub(r'\b([a-zA-Z])\'', r'~\1', expr)
        expr = re.sub(r'\b[a-z]\b', lambda m: m.group(0).upper(), expr)
        
        expr = expr.replace('+', '|')
        expr = expr.replace('.', '&')
        
        return "".join(expr.split())

    def extrair_variaveis(self, expressoes: list) -> list:
        variaveis = set()
        for expr in expressoes:
            expr_norm = self.normalizar_expressao(expr)
            encontradas = re.findall(r'\b[a-zA-Z]\b', expr_norm)
            variaveis.update([v.upper() for v in encontradas])
        return sorted(list(variaveis))

    def preparar_expressao(self, expressao: str) -> str:
        """Traduz a expressão para a sintaxe segura do Python sem loops estruturais."""
        expr_traduzida = self.normalizar_expressao(expressao)
        
        # Substitui até 5 níveis de negação (suficiente e seguro contra loops infinitos)
        for _ in range(5):
            if '~' not in expr_traduzida:
                break
            expr_traduzida = re.sub(r'~([^()~&|+\-<>]+|\([^()]*\))', r'(not \1)', expr_traduzida)

        for logico, python in self.REPLACEMENTS:
            expr_traduzida = expr_traduzida.replace(logico, python)
            
        return expr_traduzida

    def avaliar_linha(self, expressao_preparada: str, contexto: dict) -> bool:
        try:
            return bool(eval(expressao_preparada, {}, contexto))
        except Exception:
            raise SyntaxError("Erro de sintaxe na expressão. Verifique os parênteses e conectivos.")

    def gerar_combinacoes(self, variaveis: list) -> list:
        return list(itertools.product([True, False], repeat=len(variaveis)))

    def formatar_booleano(self, valor: bool) -> str:
        return 'V' if valor else 'F'

    def processar_equivalencia(self, expr1: str, expr2: str):
        variaveis = self.extrair_variaveis([expr1, expr2])
        expr1_prep = self.preparar_expressao(expr1)
        expr2_prep = self.preparar_expressao(expr2)
        combinacoes = self.gerar_combinacoes(variaveis)

        linhas_tabela = []
        equivalentes = True

        for combo in combinacoes:
            contexto = dict(zip(variaveis, combo))
            res1 = self.avaliar_linha(expr1_prep, contexto)
            res2 = self.avaliar_linha(expr2_prep, contexto)

            if res1 != res2:
                equivalentes = False

            linha = {v: self.formatar_booleano(contexto[v]) for v in variaveis}
            linha[self.normalizar_expressao(expr1)] = self.formatar_booleano(res1)
            linha[self.normalizar_expressao(expr2)] = self.formatar_booleano(res2)
            linhas_tabela.append(linha)

        return pd.DataFrame(linhas_tabela), equivalentes

    def explicar_argumento(self, premissas: list, conclusao: str, eh_valido: bool) -> str:
        p_norm = [self.normalizar_expressao(p) for p in premissas]
        c_norm = self.normalizar_expressao(conclusao)
        p_set = set(p_norm)

        if eh_valido:
            for p in p_norm:
                if "->" in p and "<->" not in p:
                    antecedente, consequente = p.split("->", 1)
                    if antecedente in p_set and c_norm == consequente:
                        return f"**Regra Identificada:** Modus Ponens (MP)\n\n**Explicação:** A partir de `{antecedente}->{consequente}` e `{antecedente}`, infere-se `{consequente}`."

            for p in p_norm:
                if "->" in p and "<->" not in p:
                    antecedente, consequente = p.split("->", 1)
                    neg_consequente = f"~{consequente}" if not consequente.startswith("~") else consequente[1:]
                    neg_antecedente = f"~{antecedente}" if not antecedente.startswith("~") else antecedente[1:]
                    if neg_consequente in p_set and c_norm == neg_antecedente:
                        return f"**Regra Identificada:** Modus Tollens (MT)\n\n**Explicação:** A partir de `{antecedente}->{consequente}` e `{neg_consequente}`, infere-se `{neg_antecedente}`."

            condicionais = [p for p in p_norm if "->" in p and "<->" not in p]
            if len(condicionais) >= 2:
                for p1 in condicionais:
                    a, b = p1.split("->", 1)
                    for p2 in condicionais:
                        if p1 != p2:
                            b2, c = p2.split("->", 1)
                            if b == b2 and (c_norm == f"{a}->{c}" or c_norm == p1 or c_norm == p2):
                                return f"**Regra Identificada:** Silogismo Hipotético (SH)\n\n**Explicação:** Encadeamento lógico condicional provado com sucesso."

            return "**Regra Identificada:** Dedução Válida Geral.\n\n**Explicação:** O argumento foi validado com sucesso através da tabela-verdade."
        else:
            return "**Falácia Identificada:** Falácia Lógica Geral.\n\n**Por que é inválido?** Existem cenários onde as premissas são Verdadeiras mas a conclusão é Falsa."

    def processar_argumento(self, premissas: list, conclusao: str):
        todas_expressoes = premissas + [conclusao]
        variaveis = self.extrair_variaveis(todas_expressoes)
        premissas_prep = [self.preparar_expressao(p) for p in premissas]
        conclusao_prep = self.preparar_expressao(conclusao)
        combinacoes = self.gerar_combinacoes(variaveis)

        linhas_tabela = []
        argumento_valido = True

        for combo in combinacoes:
            contexto = dict(zip(variaveis, combo))
            valores_premissas = [self.avaliar_linha(p, contexto) for p in premissas_prep]
            valor_conclusao = self.avaliar_linha(conclusao_prep, contexto)

            eh_falacia_na_linha = all(valores_premissas) and not valor_conclusao
            if eh_falacia_na_linha:
                argumento_valido = False

            linha = {v: self.formatar_booleano(contexto[v]) for v in variaveis}
            for i, p_val in enumerate(valores_premissas):
                linha[f"Premissa {i+1}"] = self.formatar_booleano(p_val)
            
            linha["Conclusão"] = self.formatar_booleano(valor_conclusao)
            linha["Validação"] = "❌ FALÁCIA" if eh_falacia_na_linha else "✅ OK"
            linhas_tabela.append(linha)

        df = pd.DataFrame(linhas_tabela)
        explicacao = self.explicar_argumento(premissas, conclusao, argumento_valido)
        return df, argumento_valido, explicacao


# =====================================================================
#                         INTERFACE STREAMLIT
# =====================================================================

st.set_page_config(page_title="Motor Lógico - UFN", page_icon="🧠", layout="wide")

st.title("🧠 Protótipo de Motor Lógico em Python")
st.markdown("*Desenvolvido para a disciplina de Lógica para Computação.*")

# --- BARRA LATERAL ---
st.sidebar.header("🔌 Guia de Conectivos")
st.sidebar.markdown("""
* **Negação:** `~p` ou `p'`
* **Conjunção:** `p & q` ou `p . q`
* **Disjunção:** `p | q` ou `p + q`
* **Condicional:** `p -> q`
* **Bicondicional:** `p <-> q`
""")

motor = MotorLogico()

tab_interpretador, tab_equiv, tab_inferencia = st.tabs([
    "Módulo A: Interpretador de Expressões",
    "Módulo B: Provador de Equivalência",
    "Módulo C: Motor de Inferência (Validador)"
])

# --- MÓDULO A ---
with tab_interpretador:
    st.header("Módulo A: Interpretador e Normalizador de Fórmulas")
    
    # Uso de formulário para evitar processamento em tempo real a cada letra digitada (previne congelamento)
    with st.form(key="form_interpretador"):
        expressao_teste = st.text_input("Insira uma expressão lógica para teste:", value="~A -> (B . c)'")
        botao_interpretar = st.form_submit_button("Analisar Expressão")
        
    if botao_interpretar and expressao_teste:
        try:
            expr_normalizada = motor.normalizar_expressao(expressao_teste)
            expr_python = motor.preparar_expressao(expressao_teste)
            variaveis_detectadas = motor.extrair_variaveis([expressao_teste])
            
            col_a1, col_a2 = st.columns(2)
            with col_a1:
                st.info(f"**Expressão Padronizada (Motor):** `{expr_normalizada}`")
                st.success(f"**Tradução Interna Python:** `{expr_python}`")
            with col_a2:
                st.metric("Variáveis Identificadas", ", ".join(variaveis_detectadas) if variaveis_detectadas else "Nenhuma")
        except Exception as e:
            st.error(f"Erro no interpretador: {e}")

# --- MÓDULO B ---
with tab_equiv:
    st.header("Verificador de Equivalência Lógica")
    
    with st.form(key="form_equivalencia"):
        col1, col2 = st.columns(2)
        with col1:
            e1 = st.text_input("Primeira Expressão:", value="A -> B")
        with col2:
            e2 = st.text_input("Segunda Expressão:", value="~B -> ~A")
        botao_equiv = st.form_submit_button("Calcular Equivalência")

    if botao_equiv:
        if e1 and e2:
            try:
                df_resultado, sao_equivalentes = motor.processar_equivalencia(e1, e2)
                if sao_equivalentes:
                    st.success("### 🟩 Resposta: Expressões LOGICAMENTE EQUIVALENTES")
                else:
                    st.error("### 🟥 Resposta: Expressões NÃO SÃO EQUIVALENTES")
                st.dataframe(df_resultado, use_container_width=True)
            except Exception as e:
                st.error(f"Erro ao processar: {e}")

# --- MÓDULO C ---
with tab_inferencia:
    st.header("Validador de Argumentos Lógicos")

    if 'num_premissas' not in st.session_state:
        st.session_state.num_premissas = 1

    # Botões de controlo de linhas fora do formulário mudam apenas o estado numérico
    col_btn1, col_btn2, _ = st.columns([1, 1, 4])
    with col_btn1:
        if st.button("➕ Adicionar Linha de Entrada"):
            st.session_state.num_premissas += 1
            st.rerun()
    with col_btn2:
        if st.button("➖ Remover Linha de Entrada") and st.session_state.num_premissas > 1:
            st.session_state.num_premissas -= 1
            st.rerun()

    # O processamento pesado e as caixas ficam protegidos dentro do Form
    with st.form(key="form_inferencia"):
        premissas_inputs = []
        st.write("#### Premissas:")
        for i in range(st.session_state.num_premissas):
            val_default = "p + r, p + r'" if i == 0 else ""
            p_in = st.text_input(f"Entrada {i+1}:", value=val_default, key=f"premissa_input_{i}")
            premissas_inputs.append(p_in)

        st.write("#### Conclusão:")
        conclusao_input = st.text_input("Conclusão do Argumento:", value="p")
        
        botao_inferir = st.form_submit_button("Avaliar Validade do Argumento")

    if botao_inferir:
        premissas_finais = []
        for item in premissas_inputs:
            if item.strip():
                if "," in item:
                    premissas_finais.extend([sub.strip() for sub in item.split(",") if sub.strip()])
                else:
                    premissas_finais.append(item.strip())

        if premissas_finais and conclusao_input:
            try:
                df_argumento, eh_valido, explicacao = motor.processar_argumento(premissas_finais, conclusao_input)
                if eh_valido:
                    st.success("### 🟩 Veredito: O argumento é VÁLIDO")
                else:
                    st.error("### 🟥 Veredito: O argumento é INVÁLIDO")
                st.info(explicacao)
                st.dataframe(df_argumento, use_container_width=True)
            except Exception as e:
                st.error(f"Erro ao processar o argumento: {e}")
