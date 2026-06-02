import streamlit as st
import pandas as pd
import itertools
import re

class MotorLogico:
    def __init__(self):
        # Mapeamento de conectivos para operadores válidos do Python
        self.REPLACEMENTS = [
            ('<->', '=='),
            ('->', ' <= '),  # P -> Q é equivalente a P <= Q em lógica booleana no Python
            ('~', ' not '),
            ('&', ' and '),
            ('|', ' or ')
        ]

    def extrair_variaveis(self, expressoes: list) -> list:
        """Extrai todas as variáveis proposicionais (letras maiúsculas) isoladas."""
        variaveis = set()
        for expr in expressoes:
            encontradas = re.findall(r'\b[A-Z]\b', expr)
            variaveis.update(encontradas)
        return sorted(list(variaveis))

    def preparar_expressao(self, expressao: str) -> str:
        """Traduz os conectivos lógicos da string para a sintaxe do Python."""
        expr_traduzida = expressao
        for logico, python in self.REPLACEMENTS:
            expr_traduzida = expr_traduzida.replace(logico, python)
        return expr_traduzida

    def avaliar_linha(self, expressao_preparada: str, contexto: dict) -> bool:
        """Avalia o valor-verdade de uma expressão usando o eval nativo."""
        try:
            return bool(eval(expressao_preparada, {}, contexto))
        except Exception as e:
            raise SyntaxError(f"Erro de sintaxe na expressão. Verifique os parênteses e conectivos.")

    def gerar_combinacoes(self, variaveis: list) -> list:
        """Gera a árvore de possibilidades binárias (True/False)."""
        return list(itertools.product([True, False], repeat=len(variaveis)))

    def formatar_booleano(self, valor: bool) -> str:
        """Mapeia True/False para V/F para exibição acadêmica."""
        return 'V' if valor else 'F'

    # --- PROCESSAMENTO PARA O MÓDULO B ---
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

            # Monta a linha estruturada para o DataFrame do Streamlit
            linha = {v: self.formatar_booleano(contexto[v]) for v in variaveis}
            linha[expr1] = self.formatar_booleano(res1)
            linha[expr2] = self.formatar_booleano(res2)
            linhas_tabela.append(linha)

        df = pd.DataFrame(linhas_tabela)
        return df, equivalentes

    # --- PROCESSAMENTO PARA O MÓDULO C ---
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

            # Um argumento é inválido se as premissas forem V e a conclusão for F
            eh_falacia_na_linha = all(valores_premissas) and not valor_conclusao
            if eh_falacia_na_linha:
                argumento_valido = False

            linha = {v: self.formatar_booleano(contexto[v]) for v in variaveis}
            for i, p_val in enumerate(valores_premissas):
                linha[f"Premissa {i+1} ({premissas[i]})"] = self.formatar_booleano(p_val)
            
            linha[f"Conclusão ({conclusao})"] = self.formatar_booleano(valor_conclusao)
            linha["Validação"] = "❌ FALÁCIA" if eh_falacia_na_linha else "✅ OK"
            linhas_tabela.append(linha)

        df = pd.DataFrame(linhas_tabela)
        return df, argumento_valido


# =====================================================================
#                         INTERFACE STREAMLIT
# =====================================================================

st.set_page_config(page_title="Motor Lógico - UFN", page_icon="🧠", layout="wide")

st.title("🧠 Protótipo de Motor Lógico em Python")
st.markdown("""
Mapeamento de Tabelas-Verdade, Equivalências e Motores de Inferência Aplicados à IA.  
*Desenvolvido para a disciplina de Lógica para Computação (Prof. Leandro Ribeiro Fontoura).*
""")

st.sidebar.header("Guia de Conectivos")
st.sidebar.markdown("""
Use a seguinte sintaxe para as expressões:
* **Negação:** `~P`
* **Conjunção (E):** `P & Q`
* **Disjunção (OU):** `P | Q`
* **Condicional:** `P -> Q`
* **Bicondicional:** `P <-> Q`
* *Use letras maiúsculas para as variáveis (P, Q, R, S).*
""")

motor = MotorLogico()

# Criação das abas para organização do Trabalho Prático
tab_equiv, tab_inferencia = st.tabs([
    "Módulo B: Provador de Equivalência", 
    "Módulo C: Motor de Inferência (Validador)"
])

# --- ABA: PROVADOR DE EQUIVALÊNCIA ---
with tab_equiv:
    st.header("Verificador de Equivalência Lógica")
    st.write("Insira duas expressões para verificar se elas possuem tabelas-verdade idênticas (Ex: Leis de De Morgan).")
    
    col1, col2 = st.columns(2)
    with col1:
        e1 = st.text_input("Primeira Expressão (Entrada 1):", value="~(P & Q)")
    with col2:
        e2 = st.text_input("Segunda Expressão (Entrada 2):", value="~P | ~Q")

    if st.button("Calcular Equivalência", key="btn_equiv"):
        if e1 and e2:
            try:
                df_resultado, sao_equivalentes = motor.processar_equivalencia(e1, e2)
                
                # Exibição do Veredito
                if sao_equivalentes:
                    st.success("### 🟩 Resposta: Expressões LOGICAMENTE EQUIVALENTES")
                else:
                    st.error("### 🟥 Resposta: Expressões NÃO SÃO EQUIVALENTES")
                
                # Renderização da Tabela Verdade Completa
                st.write("#### Tabela-Verdade Gerada:")
                st.dataframe(df_resultado, use_container_width=True)
                
            except Exception as e:
                st.error(f"Erro ao processar: {e}")
        else:
            st.warning("Por favor, preencha ambas as expressões.")

# --- ABA: MOTOR DE INFERÊNCIA ---
with tab_inferencia:
    st.header("Validador de Argumentos Lógicos")
    st.write("Defina um conjunto de premissas e veja se a conclusão decorre logicamente delas.")

    # Controle dinâmico do número de premissas usando a sessão do Streamlit
    if 'num_premissas' not in st.session_state:
        st.session_state.num_premissas = 2

    col_btn1, col_btn2, _ = st.columns([1, 1, 4])
    with col_btn1:
        if st.button("➕ Adicionar Premissa"):
            st.session_state.num_premissas += 1
    with col_btn2:
        if st.button("➖ Remover Premissa") and st.session_state.num_premissas > 1:
            st.session_state.num_premissas -= 1

    # Inputs das premissas dinâmicas
    premissas_inputs = []
    st.write("#### Premissas:")
    
    # Valores default para ilustrar o Modus Ponens no primeiro carregamento
    defaults_premissas = ["P -> Q", "P"]
    
    for i in range(st.session_state.num_premissas):
        val_default = defaults_premissas[i] if i < len(defaults_premissas) else ""
        p_in = st.text_input(f"Premissa {i+1}:", value=val_default, key=f"premissa_{i}")
        if p_in:
            premissas_inputs.append(p_in)

    st.write("#### Conclusão:")
    conclusao_input = st.text_input("Conclusão do Argumento:", value="Q", key="conclusao")

    if st.button("Avaliar Validade do Argumento", key="btn_infer"):
        if premissas_inputs and conclusao_input:
            try:
                df_argumento, eh_valido = motor.processar_argumento(premissas_inputs, conclusao_input)
                
                if eh_valido:
                    st.success("### 🟩 Veredito: O argumento é VÁLIDO (Dedução Legítima)")
                else:
                    st.error("### 🟥 Veredito: O argumento é INVÁLIDO (Falácia Lógica)")
                    st.info("💡 Uma falácia ocorre quando todas as premissas são Verdadeiras (V), mas a conclusão é Falsa (F). Veja as linhas sinalizadas na tabela abaixo.")

                st.write("#### Análise da Tabela-Verdade do Argumento:")
                
                # Destaca visualmente a linha onde a falácia acontece se houver
                st.dataframe(df_argumento, use_container_width=True)
                
            except Exception as e:
                st.error(f"Erro ao processar o argumento: {e}")
        else:
            st.warning("Certifique-se de preencher as premissas e a conclusão.")
