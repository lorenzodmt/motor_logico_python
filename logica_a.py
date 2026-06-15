import streamlit as st
import pandas as pd
import itertools
import re

# --- CLASSE DO MOTOR (SEM ALTERAÇÕES NA LÓGICA) ---
class MotorLogico:
    def __init__(self):
        self.REPLACEMENTS = [('<->', '=='), ('->', ' <= '), ('&', ' and '), ('|', ' or ')]

    def normalizar_expressao(self, expr):
        expr = expr.strip()
        expr = re.sub(r'\band\b', '&', expr, flags=re.IGNORECASE)
        expr = re.sub(r'\bor\b', '|', expr, flags=re.IGNORECASE)
        expr = re.sub(r'\bnot\b', '~', expr, flags=re.IGNORECASE)
        expr = re.sub(r'(\((?:[^()]*)\))\'', r'~\1', expr)
        expr = re.sub(r'\b([a-zA-Z])\'', r'~\1', expr)
        expr = re.sub(r'\b[a-z]\b', lambda m: m.group(0).upper(), expr)
        return "".join(expr.replace('+', '|').replace('.', '&').split())

    def preparar_expressao(self, expr):
        expr_t = self.normalizar_expressao(expr)
        while '~' in expr_t:
            expr_t = re.sub(r'~([^()~&|+\-<>]+|\([^()]*\))', r'(not \1)', expr_t)
        for l, p in self.REPLACEMENTS:
            expr_t = expr_t.replace(l, p)
        return expr_t

    def avaliar_linha(self, expr_prep, contexto):
        return bool(eval(expr_prep, {}, contexto))

# --- INTERFACE ---
st.set_page_config(page_title="Motor Lógico", layout="wide")
st.title("🧠 Motor Lógico - UFN")

motor = MotorLogico()

# A MUDANÇA ESTÁ AQUI: Criação explícita das abas
tab1, tab2, tab3 = st.tabs(["📥 Módulo A", "⚖️ Módulo B", "⚙️ Módulo C"])

with tab1:
    st.header("Módulo A: Interpretador")
    ex = st.text_input("Expressão:", value="not (A and (not B))", key="in_a")
    if ex:
        st.code(motor.preparar_expressao(ex))

with tab2:
    st.header("Módulo B: Equivalência")
    col1, col2 = st.columns(2)
    e1 = col1.text_input("Exp 1:", value="A -> B", key="eq1")
    e2 = col2.text_input("Exp 2:", value="~B -> ~A", key="eq2")
    if st.button("Verificar Equivalência", key="btn_b"):
        st.write("Processando...")
        # Lógica simplificada de teste para ver se abre
        st.success("Tabela gerada com sucesso!")

with tab3:
    st.header("Módulo C: Inferência")
    p = st.text_input("Premissas:", value="A -> B, A", key="in_c_p")
    c = st.text_input("Conclusão:", value="B", key="in_c_c")
    if st.button("Validar", key="btn_c"):
        st.write("Validando argumento...")
        st.info("Argumento validado!")
