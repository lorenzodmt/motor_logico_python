import streamlit as st
import pandas as pd
import itertools
import re

# =====================================================================
#                         MOTOR LÓGICO CORRIGIDO
# =====================================================================
class MotorLogico:
    def __init__(self):
        # Módulo A: Mapeamento sugerido para os operadores padrão do Python
        self.REPLACEMENTS = [
            ('<->', '=='),
            ('->', ' <= '),
            ('&', ' and '),
            ('|', ' or ')
        ]

    def normalizar_expressao(self, expressao: str) -> str:
        """Módulo A: Normaliza strings e padroniza conectivos."""
        if not expressao:
            return ""
        expr = expressao.strip()
        
        # Ignora maiúsculas/minúsculas para operadores textuais nativos
        expr = re.sub(r'\band\b', '&', expr, flags=re.IGNORECASE)
        expr = re.sub(r'\bor\b', '|', expr, flags=re.IGNORECASE)
        expr = re.sub(r'\bnot\b', '~', expr, flags=re.IGNORECASE)

        # Trata as negações pós-fixadas (')
        while ")'" in expr:
            expr = re.sub(r'(\((?:[^()]*)\))\'', r'~\1', expr)
        expr = re.sub(r'\b([a-zA-Z])\'', r'~\1', expr)
        
        # Variáveis em maiúsculo
        expr = re.sub(r'\b[a-z]\b', lambda m: m.group(0).upper(), expr)
        
        # Conectivos alternativos acadêmicos (+ e .)
        expr = expr.replace('+', '|')
        expr = expr.replace('.', '&')
        
        return "".join(expr.split())

    def extrair_variaveis(self, expressoes: list) -> list:
        """Módulo A: Extrai variáveis proposicionais únicas."""
        variaveis = set()
        for expr in expressoes:
            expr_norm = self.normalizar_expressao(expr)
            encontradas = re.findall(r'\b[a-zA-Z]\b', expr_norm)
            variaveis.update([v.upper() for v in encontradas])
        return sorted(list(variaveis))

    def preparar_expressao(self, expressao: str) -> str:
        """Módulo A: Mapeia caracteres para operadores válidos do Python."""
        expr_traduzida = self.normalizar_expressao(expressao)
        
        # Envelopa a negação para garantir precedência no eval
        while '~' in expr_traduzida:
            expr_traduzida = re.sub(r'~([^()~&|+\-<>]+|\([^()]*\))', r'(not \1)', expr_traduzida)

        for logico, python in self.REPLACEMENTS:
            expr_traduzida = expr_traduzida.replace(logico, python)
            
        return expr_traduzida

    def avaliar_linha(self, expressao_preparada: str, contexto: dict) -> bool:
        """Avalia o valor booleano usando o eval nativo."""
        try:
            return bool(eval(expressao_preparada, {}, contexto))
        except Exception:
            raise SyntaxError("Erro de sintaxe na expressão.")

    def gerar_combinacoes(self, variaveis: list) -> list:
        return list(itertools.product([True, False], repeat=len(variaveis)))

    def formatar_booleano(self, valor: bool) -> str:
        return 'V' if valor else 'F'

    # --- MÓDULO B: PROVADOR DE EQUIVALÊNCIA ---
    def processar_equivalencia(self, expr1: str, expr2: str):
        variaveis = self.extrair_variaveis([expr1, expr2])
        expr1_prep = self.preparar_expressao(expr1)
        expr2_prep = self.preparar_expressao(expr2)
        combinacoes = self.gerar_combinacoes(variaveis)  # CORRIGIDO AQUI!

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

    # --- MÓDULO C: MOTOR DE INFERÊNCIA ---
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
                p_nome_norm = self.normalizar_expressao(premissas[i])
                linha[f"Premissa {i+1} ({p_nome_norm})"] = self.formatar_booleano(p_val)
            
            c_nome_norm = self.normalizar_expressao(conclusao)
            linha[f"Conclusão ({c_nome_norm})"] = self.formatar_booleano(valor_conclusao)
            linha["Validação"] = "❌ FALÁCIA" if eh_falacia_na_linha else "✅ OK"
            linhas_tabela.append(linha)

        return pd.DataFrame(linhas_tabela), argumento_valido


# =====================================================================
#                         INTERFACE STREAMLIT
# =====================================================================

st.set_page_config(page_title="Motor Lógico - UFN", page_icon="🧠", layout="wide")

# Inicialização do Motor
motor = MotorLogico()

# 1. BARRA LATERAL (SIDEBAR)
st.sidebar.header("🔌 Guia de Conectivos")
st.sidebar.markdown("""
Use qualquer uma das sintaxes abaixo:
* **Negação:** `~P`, `not P` ou `P'`
* **Conjunção:** `P & Q`, `P and Q` ou `P . Q`
* **Disjunção:** `P | Q`, `P or Q` ou `P + Q`
* **Condicional:** `P -> Q`
* **Bicondicional:** `P <-> Q`
""")
st.sidebar.markdown("---")
st.sidebar.header("📜 Casos de Teste")
st.sidebar.info("**Contrapositiva:**\n* Entrada 1: `A -> B`\n* Entrada 2: `~B -> ~A`")

# 2. CORPO PRINCIPAL
st.title("🧠 Protótipo de Motor Lógico em Python")
st.markdown("Mapeamento de Tabelas-Verdade, Equivalências e Motores de Inferência Aplicados à IA.")

# Criação das Abas Separadas
tab_a, tab_b, tab_c = st.tabs([
    "📥 Módulo A: Interpretador", 
    "⚖️ Módulo B: Equivalência", 
    "⚙️ Módulo C: Inferência"
])

# --- ABA A ---
with tab_a:
    st.header("Módulo A: Interpretador de Expressões")
    input_a = st.text_input("Digite uma expressão lógica para teste:", value="not (A and (not B))", key="txt_a")
    if input_a:
        try:
            norm = motor.normalizar_expressao(input_a)
            prep = motor.preparar_expressao(input_a)
            v_det = motor.extrair_variaveis([input_a])
            
            c1, c2 = st.columns(2)
            c1.info(f"**Expressão Padronizada:** `{norm}`")
            c1.success(f"**Tradução Python (`eval`):** `{prep}`")
            c2.metric("Variáveis Detectadas", ", ".join(v_det) if v_det else "Nenhuma")
        except Exception as e:
            st.error(f"Erro no interpretador: {e}")

# --- ABA B ---
with tab_b:
    st.header("Módulo B: Provador de Equivalência")
    col_b1, col_b2 = st.columns(2)
    expr_b1 = col_b1.text_input("Primeira Expressão (Entrada 1):", value="A -> B", key="txt_b1")
    expr_b2 = col_b2.text_input("Segunda Expressão (Entrada 2):", value="~B -> ~A", key="txt_b2")
    
    if st.button("Calcular Tabela e Verificar", key="btn_b"):
        if expr_b1 and expr_b2:
            try:
                df_b, sao_equivalentes = motor.processar_equivalencia(expr_b1, expr_b2)
                if sao_equivalentes:
                    st.success("### 🟩 Resposta: Expressões LOGICAMENTE EQUIVALENTES")
                else:
                    st.error("### 🟥 Resposta: Expressões NÃO SÃO EQUIVALENTES")
                st.dataframe(df_b, use_container_width=True)
            except Exception as e:
                st.error(f"Erro ao processar equivalência: {e}")

# --- ABA C ---
with tab_c:
    st.header("Módulo C: Motor de Inferência")
    premissas_in = st.text_input("Premissas (separadas por vírgula):", value="A -> B, A", key="txt_c_p")
    conclusao_in = st.text_input("Conclusão:", value="B", key="txt_c_c")
    
    if st.button("Avaliar Validade do Argumento", key="btn_c"):
        if premissas_in and conclusao_in:
            try:
                lista_p = [p.strip() for p in premissas_in.split(",") if p.strip()]
                df_c, eh_valido = motor.processar_argumento(lista_p, conclusao_in)
                if eh_valido:
                    st.success("### 🟩 Veredito: O argumento é VÁLIDO")
                else:
                    st.error("### 🟥 Veredito: O argumento é INVÁLIDO")
                st.dataframe(df_c, use_container_width=True)
            except Exception as e:
                st.error(f"Erro ao processar inferência: {e}")
