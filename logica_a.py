import streamlit as st
import pandas as pd
import itertools
import re

class MotorLogico:
    def __init__(self):
        # Mapeamento de conectivos para operadores válidos do Python
        self.REPLACEMENTS = [
            ('<->', '=='),
            ('->', ' <= '),  # P -> Q é equivalente a P <= Q em lógica booleana
            ('&', ' and '),
            ('|', ' or ')
        ]

    def normalizar_expressao(self, expressao: str) -> str:
        """Módulo A: Normaliza e padroniza a string de entrada para a sintaxe do motor."""
        expr = expressao.strip()
        
        # 1. Trata a negação com aspa simples após fechar parênteses (Ex: (p.q)' vira ~(p.q))
        while ")'" in expr:
            expr = re.sub(r'(\((?:[^()]*)\))\'', r'~\1', expr)
        
        # 2. Trata a negação pós-fixada de variáveis isoladas (Ex: p' ou P' vira ~P)
        expr = re.sub(r'\b([a-zA-Z])\'', r'~\1', expr)
        
        # 3. Converte todas as variáveis proposicionais isoladas para maiúsculas
        expr = re.sub(r'\b[a-z]\b', lambda m: m.group(0).upper(), expr)
        
        # 4. Padroniza os conectivos alternativos acadêmicos para os símbolos padrão do motor
        expr = expr.replace('+', '|')  # Disjunção (OU)
        expr = expr.replace('.', '&')  # Conjunção (E)
        
        return "".join(expr.split())

    def extrair_variaveis(self, expressoes: list) -> list:
        """Módulo A: Extrai todas as variáveis proposicionais limpas (letras isoladas)."""
        variaveis = set()
        for expr in expressoes:
            expr_norm = self.normalizar_expressao(expr)
            encontradas = re.findall(r'\b[a-zA-Z]\b', expr_norm)
            variaveis.update([v.upper() for v in encontradas])
        return sorted(list(variaveis))

    def preparar_expressao(self, expressao: str) -> str:
        """Módulo A: Mapeia caracteres legíveis para os operadores padrão do Python (eval)."""
        expr_traduzida = self.normalizar_expressao(expressao)
        
        # Resolve a precedência e sintaxe da negação (not) no Python
        while '~' in expr_traduzida:
            expr_traduzida = re.sub(r'~([^()~&|+\-<>]+|\([^()]*\))', r'(not \1)', expr_traduzida)

        # Traduz os demais conectivos relacionais mapeados para o interpretador Python
        for logico, python in self.REPLACEMENTS:
            expr_traduzida = expr_traduzida.replace(logico, python)
            
        return expr_traduzida

    def avaliar_linha(self, expressao_preparada: str, contexto: dict) -> bool:
        """Avalia computacionalmente o valor-verdade de uma expressão interpretada."""
        try:
            return bool(eval(expressao_preparada, {}, contexto))
        except Exception as e:
            raise SyntaxError(f"Erro de sintaxe na expressão. Verifique os parênteses e conectivos.")

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

        df = pd.DataFrame(linhas_tabela)
        return df, equivalentes

    def explicar_argumento(self, premissas: list, conclusao: str, eh_valido: bool) -> str:
        p_norm = [self.normalizar_expressao(p) for p in premissas]
        c_norm = self.normalizar_expressao(conclusao)
        p_set = set(p_norm)

        if eh_valido:
            # 1. MODUS PONENS (MP)
            for p in p_norm:
                if "->" in p and "<->" not in p:
                    antecedente, consequente = p.split("->", 1)
                    if antecedente in p_set and c_norm == consequente:
                        return f"**Regra Identificada:** Modus Ponens (MP)\n\n" \
                               f"**Explicação:** A partir de `{antecedente}->{consequente}` e `{antecedente}`, infere-se `{consequente}`."

            # 2. MODUS TOLLENS (MT)
            for p in p_norm:
                if "->" in p and "<->" not in p:
                    antecedente, consequente = p.split("->", 1)
                    neg_consequente = f"~{consequente}" if not consequente.startswith("~") else consequente[1:]
                    neg_antecedente = f"~{antecedente}" if not antecedente.startswith("~") else antecedente[1:]
                    if neg_consequente in p_set and c_norm == neg_antecedente:
                        return f"**Regra Identificada:** Modus Tollens (MT)\n\n" \
                               f"**Explicação:** A partir de `{antecedente}->{consequente}` e `{neg_consequente}`, infere-se `{neg_antecedente}`."

            # 3. SILOGISMO HIPOTÉTICO (SH)
            condicionais = [p for p in p_norm if "->" in p and "<->" not in p]
            if len(condicionais) >= 2:
                for p1 in condicionais:
                    a, b = p1.split("->", 1)
                    for p2 in condicionais:
                        if p1 != p2:
                            b2, c = p2.split("->", 1)
                            if b == b2 and (c_norm == f"{a}->{c}" or c_norm == p1 or c_norm == p2):
                                return f"**Regra Identificada:** Silogismo Hipotético (SH)\n\n" \
                                       f"**Explicação:** Encadeamento lógico estruturado de causa e efeito demonstrado com sucesso."

            # 4. SILOGISMO DISJUNTIVO (SD)
            for p in p_norm:
                if "|" in p:
                    partes = p.split("|")
                    if len(partes) == 2:
                        a, b = partes[0], partes[1]
                        neg_a = f"~{a}" if not a.startswith("~") else a[1:]
                        neg_b = f"~{b}" if not b.startswith("~") else b[1:]
                        if (neg_a in p_set and c_norm == b) or (neg_b in p_set and c_norm == a):
                            return f"**Regra Identificada:** Silogismo Disjuntivo (SD)\n\n" \
                                   f"**Explicação:** Eliminando uma das alternativas da disjunção por sua negação, conclui-se a outra."

            # 7. SIMPLIFICAÇÃO (S)
            for p in p_norm:
                if "&" in p:
                    partes_p = p.split("&")
                    if c_norm in partes_p:
                        return f"**Regra Identificada:** Simplificação (S)\n\n" \
                               f"**Explicação:** De uma conjunção (`{p}`), extrai-se legitimamente qualquer um dos componentes independentes."

            # 8. SIMPLIFICAÇÃO DISJUNTIVA (S+)
            for p in p_norm:
                if "|" in p and p.split("|")[0] == p.split("|")[1] and c_norm == p.split("|")[0]:
                    return f"**Regra Identificada:** Simplificação Disjuntiva / Idempotência (S+)"
            
            # 9. UNIÃO (U)
            if "&" in c_norm:
                partes_c = c_norm.split("&")
                if len(partes_c) == 2:
                    if partes_c[0] in p_set and partes_c[1] in p_set:
                        return f"**Regra Identificada:** União (U)\n\n" \
                               f"**Explicação:** Duas premissas verdadeiras isoladas foram unidas sob o conectivo de conjunção."

            return "**Regra Identificada:** Dedução Válida Geral.\n\n" \
                   "**Explicação:** O argumento foi validado com sucesso através da matriz da tabela-verdade."
        else:
            return "**Falácia Identificada:** Falácia Lógica.\n\n" \
                   "**Por que é inválido?** A tabela-verdade provou computacionalmente que é possível obter premissas verdadeiras com uma conclusão falsa."

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

# --- INSTANCIAÇÃO DO MOTOR ---
motor = MotorLogico()

# Definição das Abas incluindo o Módulo A como a central de Uploads/Texto
tab_modulo_a, tab_equiv, tab_inferencia = st.tabs([
    "📥 Módulo A: Interpretador & Arquivos",
    "Módulo B: Provador de Equivalência",
    "Módulo C: Motor de Inferência"
])

# --- MÓDULO A ---
with tab_modulo_a:
    st.header("Interpretador de Expressões, Textos e Arquivos")
    st.write("Insira dados de forma textual livre ou anexe um arquivo de texto contendo as expressões lógicas.")
    
    fonte_entrada = st.radio("Escolha o método de entrada do Módulo A:", ["Texto Livre / Pergunta", "Anexar Arquivo (.txt)"])
    
    premissas_carregadas = []
    conclusao_carregada = ""
    
    if fonte_entrada == "Texto Livre / Pergunta":
        texto_input = st.text_area(
            "Digite as proposições compostas (separe premissas por quebra de linha ou por vírgulas):", 
            value="A -> B\n~B -> ~A"
        )
        # Processamento simples de linhas
        linhas = [l.strip() for l in texto_input.split("\n") if l.strip()]
        if linhas:
            # Se houver mais de uma linha, assume que a última pode ser uma conclusão experimental
            premissas_carregadas = linhas[:-1] if len(linhas) > 1 else linhas
            conclusao_carregada = linhas[-1] if len(linhas) > 1 else ""

    else:
        arquivo_postado = st.file_uploader("Arraste ou selecione o arquivo de texto:", type=["txt"])
        if arquivo_postado is not None:
            conteudo_txt = arquivo_postado.read().decode("utf-8")
            st.info("📄 Arquivo lido com sucesso!")
            
            # Divide o arquivo por quebras de linha
            linhas_arquivo = [l.strip() for l in conteudo_txt.split("\n") if l.strip()]
            
            if linhas_arquivo:
                st.write("**Expressões identificadas pelo Interpretador:**")
                for index, linha in enumerate(linhas_arquivo):
                    st.code(f"Linha {index+1}: {linha}")
                
                # Mapeia automaticamente para os módulos
                premissas_carregadas = linhas_arquivo[:-1] if len(linhas_arquivo) > 1 else linhas_arquivo
                conclusao_carregada = linhas_arquivo[-1] if len(linhas_arquivo) > 1 else ""

    # Demonstração em tempo real do Mapeamento do Módulo A para Python
    if premissas_carregadas:
        st.subheader("⚙️ Mapeamento e Análise Sintática do Interpretador")
        exemplo_analise = []
        for p in premissas_carregadas:
            exemplo_analise.append({
                "Expressão Original": p,
                "Normalizado (Módulo A)": motor.normalizar_expressao(p),
                "Mapeamento Python (eval)": motor.preparar_expressao(p),
                "Variáveis Identificadas": str(motor.extrair_variaveis([p]))
            })
        st.table(pd.DataFrame(exemplo_analise))

# --- MÓDULO B ---
with tab_equiv:
    st.header("Verificador de Equivalência Lógica")
    st.write("Verifique se duas expressões possuem tabelas-verdade idênticas.")
    
    col1, col2 = st.columns(2)
    with col1:
        e1 = st.text_input("Primeira Expressão:", value="A -> B")
    with col2:
        e2 = st.text_input("Segunda Expressão:", value="~B -> ~A")

    if st.button("Calcular Equivalência", key="btn_equiv"):
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
    st.write("Insira premissas e valide se a conclusão decorre logicamente delas.")
    
    # Se existirem premissas vindas do arquivo/texto do Módulo A, sugere preenchimento automático
    sugestao_p = ", ".join(premissas_carregadas) if premissas_carregadas else "p -> q, p"
    sugestao_c = conclusao_carregada if conclusao_carregada else "q"
    
    p_input = st.text_input("Premissas (separe por vírgulas):", value=sugestao_p)
    c_input = st.text_input("Conclusão do Argumento:", value=sugestao_c)

    if st.button("Avaliar Validade do Argumento", key="btn_infer"):
        if p_input and c_input:
            try:
                lista_premissas = [item.strip() for item in p_input.split(",") if item.strip()]
                df_argumento, eh_valido, explicacao = motor.processar_argumento(lista_premissas, c_input)
                
                if eh_valido:
                    st.success("### 🟩 Veredito: O argumento é VÁLIDO")
                else:
                    st.error("### 🟥 Veredito: O argumento é INVÁLIDO")
                
                st.info(explicacao)
                st.dataframe(df_argumento, use_container_width=True)
            except Exception as e:
                st.error(f"Erro ao processar o argumento: {e}")
