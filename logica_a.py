import streamlit as st
import pandas as pd
import itertools
import re

class MotorLogico:
    def __init__(self):
        # Módulo A: Mapeamento sugerido de caracteres legíveis para os operadores padrão do Python
        self.REPLACEMENTS = [
            ('<->', '=='),
            ('->', ' <= '),  # P -> Q é equivalente a P <= Q em lógica booleana
            ('&', ' and '),
            ('|', ' or ')
        ]

    def normalizar_expressao(self, expressao: str) -> str:
        """Módulo A: Trata a entrada de dados (strings) limpando e padronizando os conectivos."""
        expr = expressao.strip()
        
        # Trata a negação com aspa simples após fechar parênteses (Ex: (p.q)' vira ~(p.q))
        while ")'" in expr:
            expr = re.sub(r'(\((?:[^()]*)\))\'', r'~\1', expr)
        
        # Trata a negação pós-fixada de variáveis isoladas (Ex: p' ou P' vira ~P)
        expr = re.sub(r'\b([a-zA-Z])\'', r'~\1', expr)
        
        # Converte todas as variáveis proposicionais isoladas para maiúsculas
        expr = re.sub(r'\b[a-z]\b', lambda m: m.group(0).upper(), expr)
        
        # Padroniza os conectivos alternativos para os símbolos padrão do motor
        expr = expr.replace('+', '|')  # Disjunção
        expr = expr.replace('.', '&')  # Conjunção
        
        return "".join(expr.split())

    def extrair_variaveis(self, expressoes: list) -> list:
        """Módulo A: Extrai todas as variáveis proposicionais limpas da string."""
        variaveis = set()
        for expr in expressoes:
            expr_norm = self.normalizar_expressao(expr)
            encontradas = re.findall(r'\b[a-zA-Z]\b', expr_norm)
            variaveis.update([v.upper() for v in encontradas])
        return sorted(list(variaveis))

    def preparar_expressao(self, expressao: str) -> str:
        """Módulo A: Mapeia a expressão para que o Python possa computar os valores booleanos."""
        expr_traduzida = self.normalizar_expressao(expressao)
        
        # Envelopa a negação (not) para evitar quebras de precedência com o '<=' no eval
        while '~' in expr_traduzida:
            expr_traduzida = re.sub(r'~([^()~&|+\-<>]+|\([^()]*\))', r'(not \1)', expr_traduzida)

        # Mapeia os conectivos restantes para operadores Python válidos
        for logico, python in self.REPLACEMENTS:
            expr_traduzida = expr_traduzida.replace(logico, python)
            
        return expr_traduzida

    def avaliar_linha(self, expressao_preparada: str, contexto: dict) -> bool:
        """Avalia computacionalmente o valor-verdade da expressão interpretada."""
        try:
            return bool(eval(expressao_preparada, {}, contexto))
        except Exception as e:
            raise SyntaxError(f"Erro de sintaxe na expressão. Verifique os parênteses e conectivos.")

    def gerar_combinacoes(self, variaveis: list) -> list:
        return list(itertools.product([True, False], repeat=len(variaveis)))

    def formatar_booleano(self, valor: bool) -> str:
        return 'V' if valor else 'F'

    # --- MÓDULO B: PROVADOR DE EQUIVALÊNCIA ---
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

        df = pd.DataFrame(linhas_tabela)
        return df, equivalentes

    # --- MÓDULO C: REGRAS DE INFERÊNCIA ---
    def explicar_argumento(self, premissas: list, conclusao: str, eh_valido: bool) -> str:
        p_norm = [self.normalizar_expressao(p) for p in premissas]
        c_norm = self.normalizar_expressao(conclusao)
        p_set = set(p_norm)

        if eh_valido:
            # Modus Ponens (MP)
            for p in p_norm:
                if "->" in p and "<->" not in p:
                    antecedente, consequente = p.split("->", 1)
                    if antecedente in p_set and c_norm == consequente:
                        return f"**Regra Identificada:** Modus Ponens (MP)\n\n" \
                               f"**Explicação:** A partir de `{antecedente}->{consequente}` e do antecedente `{antecedente}`, infere-se `{consequente}`."

            # Modus Tollens (MT)
            for p in p_norm:
                if "->" in p and "<->" not in p:
                    antecedente, consequente = p.split("->", 1)
                    neg_consequente = f"~{consequente}" if not consequente.startswith("~") else consequente[1:]
                    neg_antecedente = f"~{antecedente}" if not antecedente.startswith("~") else antecedente[1:]
                    if neg_consequente in p_set and c_norm == neg_antecedente:
                        return f"**Regra Identificada:** Modus Tollens (MT)\n\n" \
                               f"**Explicação:** A partir de `{antecedente}->{consequente}` e da negação do consequente `{neg_consequente}`, infere-se `{neg_antecedente}`."

            # Silogismo Hipotético (SH)
            condicionais = [p for p in p_norm if "->" in p and "<->" not in p]
            if len(condicionais) >= 2:
                for p1 in condicionais:
                    a, b = p1.split("->", 1)
                    for p2 in condicionais:
                        if p1 != p2:
                            b2, c = p2.split("->", 1)
                            if b == b2 and (c_norm == f"{a}->{c}" or c_norm == p1 or c_norm == p2):
                                return f"**Regra Identificada:** Silogismo Hipotético (SH)\n\n" \
                                       f"**Explicação:** Encadeamento lógico dedutivo entre condicionais validado com sucesso."

            # Silogismo Disjuntivo (SD)
            for p in p_norm:
                if "|" in p:
                    partes = p.split("|")
                    if len(partes) == 2:
                        a, b = partes[0], partes[1]
                        neg_a = f"~{a}" if not a.startswith("~") else a[1:]
                        neg_b = f"~{b}" if not b.startswith("~") else b[1:]
                        if (neg_a in p_set and c_norm == b) or (neg_b in p_set and c_norm == a):
                            return f"**Regra Identificada:** Silogismo Disjuntivo (SD)\n\n" \
                                   f"**Explicação:** Sabendo que uma das opções da disjunção é falsa, a outra é necessariamente verdadeira."

            # Simplificação (S)
            for p in p_norm:
                if "&" in p:
                    partes_p = p.split("&")
                    if c_norm in partes_p:
                        return f"**Regra Identificada:** Simplificação (S)\n\n" \
                               f"**Explicação:** De uma conjunção (`{p}`), onde ambas as partes são verdadeiras, extrai-se legitimamente `{c_norm}`."

            # União (U)
            if "&" in c_norm:
                partes_c = c_norm.split("&")
                if len(partes_c) == 2:
                    if partes_c[0] in p_set and partes_c[1] in p_set:
                        return f"**Regra Identificada:** União (U)\n\n" \
                               f"**Explicação:** Duas premissas verdadeiras isoladas foram unidas através do conectivo de conjunção."

            return "**Regra Identificada:** Dedução Válida Geral.\n\n" \
                   "**Explicação:** O argumento foi considerado válido através do teste da matriz da tabela-verdade."
        else:
            return "**Falácia Identificada:** Falácia Lógica Geral.\n\n" \
                   "**Por que é inválido?** A tabela-verdade encontrou linhas onde todas as premissas são verdadeiras mas a conclusão é falsa."

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

        df = pd.DataFrame(linhas_tabela)
        explicao_didatica = self.explicar_argumento(premissas, conclusao, argumento_valido)
        
        return df, argumento_valido, explicao_didatica


# =====================================================================
#                         INTERFACE STREAMLIT
# =====================================================================

st.set_page_config(page_title="Motor Lógico - UFN", page_icon="🧠", layout="wide")

st.title("🧠 Protótipo de Motor Lógico em Python")
st.markdown("""
Mapeamento de Tabelas-Verdade, Equivalências e Motores de Inferência Aplicados à IA.  
*Desenvolvido para a disciplina de Lógica para Computação (Prof. Leandro Ribeiro Fontoura).*
""")

# --- BARRA LATERAL ESQUERDA (SIDEBAR) ---
st.sidebar.header("🔌 Guia de Conectivos")
st.sidebar.markdown("""
Use a seguinte sintaxe para as expressões:
* **Negação:** `~p`, `p'` ou `(p.q)'`
* **Conjunção (E):** `p & q` ou `p . q`
* **Disjunção (OU):** `p | q` ou `p + q`
* **Condicional:** `p -> q`
* **Bicondicional:** `p <-> q`
""")

st.sidebar.markdown("---")

st.sidebar.header("📜 Guia de Regras de Inferência")
with st.sidebar.expander("Modus Ponens (MP)"):
    st.markdown("**Premissas:** `p -> q, p` \n\n**Conclusão:** `q`")
with st.sidebar.expander("Modus Tollens (MT)"):
    st.markdown("**Premissas:** `p -> q, q'` \n\n**Conclusão:** `p'`")
with st.sidebar.expander("Silogismo Hipotético (SH)"):
    st.markdown("**Premissas:** `p -> q, q -> r` \n\n**Conclusão:** `p -> r`")
with st.sidebar.expander("Silogismo Disjuntivo (SD)"):
    st.markdown("**Premissas:** `p + q, p'` \n\n**Conclusão:** `q`")
with st.sidebar.expander("Simplificação (S)"):
    st.markdown("**Premissas:** `p . q` \n\n**Conclusão:** `p`")
with st.sidebar.expander("União (U)"):
    st.markdown("**Premissas:** `p, q` \n\n**Conclusão:** `p . q`")


# --- CORPO PRINCIPAL DOS MÓDULOS ---
motor = MotorLogico()

tab_modulo_a, tab_modulo_b, tab_modulo_c = st.tabs([
    "📥 Módulo A: Interpretador de Expressões",
    "⚖️ Módulo B: Verificador de Equivalência",
    "⚙️ Módulo C: Motor de Inferência"
])

# --- MÓDULO A: INTERPRETADOR DE EXPRESSÕES ---
with tab_modulo_a:
    st.header("Módulo A: Interpretador de Expressões")
    st.write("Insira uma string contendo proposições compostas e conectivos lógicos para ver como o motor mapeia para os operadores nativos do Python.")
    
    input_teste = st.text_input("Digite uma expressão de teste (Ex: (P . Q)' -> ~R + S):", value="(p . q)' -> ~r")
    
    if input_teste:
        st.subheader("Análise Sintática e Tradução do Interpretador")
        
        # Gera os dados processados pelo Módulo A
        expr_normalizada = motor.normalizar_expressao(input_teste)
        expr_python = motor.preparar_expressao(input_teste)
        vars_identificadas = motor.extrair_variaveis([input_teste])
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.info(f"**Expressão Normalizada:** `{expr_normalizada}`")
            st.success(f"**Mapeamento Python (`eval`):** `{expr_python}`")
        with col_b:
            st.metric("Variáveis Identificadas", ", ".join(vars_identificadas) if vars_identificadas else "Nenhuma")

# --- MÓDULO B: VERIFICADOR DE EQUIVALÊNCIA ---
with tab_modulo_b:
    st.header("Módulo B: Provador de Equivalência Lógica")
    st.write("Insira duas expressões para verificar se elas possuem tabelas-verdade idênticas (Ex: Contrapositiva, Leis de De Morgan).")
    
    col1, col2 = st.columns(2)
    with col1:
        e1 = st.text_input("Primeira Expressão (Entrada 1):", value="A -> B", key="eq_e1")
    with col2:
        e2 = st.text_input("Segunda Expressão (Entrada 2):", value="~B -> ~A", key="eq_e2")

    if st.button("Calcular Equivalência", key="btn_equiv"):
        if e1 and e2:
            try:
                df_resultado, sao_equivalentes = motor.processar_equivalencia(e1, e2)
                if sao_equivalentes:
                    st.success("### 🟩 Resposta: Expressões LOGICAMENTE EQUIVALENTES")
                else:
                    st.error("### 🟥 Resposta: Expressões NÃO SÃO EQUIVALENTES")
                st.write("#### Tabela-Verdade Computada:")
                st.dataframe(df_resultado, use_container_width=True)
            except Exception as e:
                st.error(f"Erro ao processar: {e}")
        else:
            st.warning("Por favor, preencha ambas as expressões.")

# --- MÓDULO C: MOTOR DE INFERÊNCIA ---
with tab_modulo_c:
    st.header("Módulo C: Motor de Inferência (Validador)")
    st.write("Defina as premissas separadas por vírgula e a conclusão para testar a validade do argumento.")

    if 'num_premissas' not in st.session_state:
        st.session_state.num_premissas = 1

    col_btn1, col_btn2, _ = st.columns([1, 1, 4])
    with col_btn1:
        if st.button("➕ Adicionar Linha de Entrada"):
            st.session_state.num_premissas += 1
    with col_btn2:
        if st.button("➖ Remover Linha de Entrada") and st.session_state.num_premissas > 1:
            st.session_state.num_premissas -= 1

    premissas_brutas = []
    st.write("#### Premissas:")
    
    defaults_premissas = ["p -> q, p"]
    
    for i in range(st.session_state.num_premissas):
        val_default = defaults_premissas[i] if i < len(defaults_premissas) else ""
        p_in = st.text_input(f"Entrada {i+1}:", value=val_default, key=f"premissa_{i}")
        if p_in.strip():
            premissas_brutas.append(p_in)

    st.write("#### Conclusão:")
    conclusao_input = st.text_input("Conclusão do Argumento:", value="q", key="conclusao")

    if st.button("Avaliar Validade do Argumento", key="btn_infer"):
        if premissas_brutas and conclusao_input:
            try:
                premissas_finais = []
                for item in premissas_brutas:
                    if "," in item:
                        sub_premissas = [sub.strip() for sub in item.split(",") if sub.strip()]
                        premissas_finais.extend(sub_premissas)
                    else:
                        premissas_finais.append(item.strip())

                df_argumento, eh_valido, explicacao = motor.processar_argumento(premissas_finais, conclusao_input)
                
                if eh_valido:
                    st.success("### 🟩 Veredito: O argumento é VÁLIDO (Dedução Legítima)")
                else:
                    st.error("### 🟥 Veredito: O argumento é INVÁLIDO (Falácia Lógica)")
                
                st.info(explicacao)

                st.write("#### Análise da Tabela-Verdade do Argumento:")
                st.dataframe(df_argumento, use_container_width=True)
                
            except Exception as e:
                st.error(f"Erro ao processar o argumento: {e}")
        else:
            st.warning("Certifique-se de preencher as premissas e a conclusão.")
