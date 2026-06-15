import streamlit as st
import pandas as pd
import itertools
import re

class MotorLogico:
    def __init__(self):
        # Mapeamento de conectivos para operadores válidos do Python
        # Ajustamos os conectivos lógicos para garantir compatibilidade de precedência no eval()
        self.REPLACEMENTS = [
            ('<->', '=='),
            ('->', ' <= '),  # P -> Q é equivalente a P <= Q em lógica booleana no Python
            ('&', ' and '),
            ('|', ' or ')
        ]

    def normalizar_expressao(self, expressao: str) -> str:
        """Converte variáveis para maiúsculas, padroniza conectivos (+, ., ') e remove espaços."""
        expr = expressao.strip()
        
        # 1. Trata a negação com aspa simples APÓS FECHAR PARÊNTESES (Ex: (p.q)' vira ~(p.q))
        while ")'" in expr:
            expr = re.sub(r'(\((?:[^()]*)\))\'', r'~\1', expr)
        
        # 2. Trata a negação pós-fixada de variáveis isoladas (Ex: p' ou P' vira ~P)
        expr = re.sub(r'\b([a-zA-Z])\'', r'~\1', expr)
        
        # 3. Converte todas as variáveis proposicionais isoladas para maiúsculas
        expr = re.sub(r'\b[a-z]\b', lambda m: m.group(0).upper(), expr)
        
        # 4. Padroniza os conectivos alternativos para os símbolos padrão do motor
        expr = expr.replace('+', '|')  # Disjunção
        expr = expr.replace('.', '&')  # Conjunção (P . Q -> P & Q)
        
        return "".join(expr.split())

    def extrair_variaveis(self, expressoes: list) -> list:
        """Extrai todas as variáveis proposicionais limpas (letras isoladas)."""
        variaveis = set()
        for expr in expressoes:
            expr_norm = self.normalizar_expressao(expr)
            encontradas = re.findall(r'\b[a-zA-Z]\b', expr_norm)
            variaveis.update([v.upper() for v in encontradas])
        return sorted(list(variaveis))

    def preparar_expressao(self, expressao: str) -> str:
        """Traduz a expressão normalizada para a sintaxe segura do Python."""
        expr_traduzida = self.normalizar_expressao(expressao)
        
        # Resolve o problema de sintaxe da negação (~): transforma '~X' em ' (not X) '
        # Isso evita que o Python quebre ao avaliar misturas de 'not' com '<='
        while '~' in expr_traduzida:
            # Captura o caractere ou bloco imediatamente após o '~' e envelopa com parênteses e not
            expr_traduzida = re.sub(r'~([^()~&|+\-<>]+|\([^()]*\))', r'(not \1)', expr_traduzida)

        # Traduz os demais conectivos relacionais e binários
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

    # --- MAPEAMENTO DAS REGRAS DE INFERÊNCIA ---
    def explicar_argumento(self, premissas: list, conclusao: str, eh_valido: bool) -> str:
        """Analisa a estrutura das premissas e conclusão para identificar e explicar a regra aplicada."""
        p_norm = [self.normalizar_expressao(p) for p in premissas]
        c_norm = self.normalizar_expressao(conclusao)
        p_set = set(p_norm)

        if eh_valido:
            # 1. MODUS PONENS (MP) -> A->B, A => B
            for p in p_norm:
                if "->" in p and "<->" not in p:
                    antecedente, consequente = p.split("->", 1)
                    if antecedente in p_set and c_norm == consequente:
                        return f"**Regra Identificada:** Modus Ponens (MP)\n\n" \
                               f"**Explicação:** A partir de uma condicional `{antecedente}->{consequente}` and da afirmação do seu antecedente `{antecedente}`, " \
                               f"infere-se legitimamente o consequente `{consequente}`."

            # 2. MODUS TOLLENS (MT) -> A->B, ~B => ~A
            for p in p_norm:
                if "->" in p and "<->" not in p:
                    antecedente, consequente = p.split("->", 1)
                    neg_consequente = f"~{consequente}" if not consequente.startswith("~") else consequente[1:]
                    neg_antecedente = f"~{antecedente}" if not antecedente.startswith("~") else antecedente[1:]
                    if neg_consequente in p_set and c_norm == neg_antecedente:
                        return f"**Regra Identificada:** Modus Tollens (MT)\n\n" \
                               f"**Explicação:** A partir de uma condicional `{antecedente}->{consequente}` e da negação do seu consequente `{neg_consequente}`, " \
                               f"infere-se a negação do seu antecedente `{neg_antecedente}`."

            # 3. SILOGISMO HIPOTÉTICO (SH) -> BUG CORRIGIDO AQUI (dicionais mudado para condicionais)
            condicionais = [p for p in p_norm if "->" in p and "<->" not in p]
            if len(condicionais) >= 2:
                for p1 in condicionais:
                    a, b = p1.split("->", 1)
                    for p2 in condicionais:
                        if p1 != p2:
                            b2, c = p2.split("->", 1)
                            if b == b2 and (c_norm == f"{a}->{c}" or c_norm == p1 or c_norm == p2):
                                return f"**Regra Identificada:** Silogismo Hipotético (SH)\n\n" \
                                       f"**Explicação:** Trata-se do estudo do encadeamento lógico condicional. Havendo premissas que conectam " \
                                       f"proposições em cadeia estruturada de causa e efeito, a validade do fluxo condicional é garantida."

            # 4. SILOGISMO DISJUNTIVO (SD) -> A|B, ~A => B
            for p in p_norm:
                if "|" in p:
                    partes = p.split("|")
                    if len(partes) == 2:
                        a, b = partes[0], partes[1]
                        neg_a = f"~{a}" if not a.startswith("~") else a[1:]
                        neg_b = f"~{b}" if not b.startswith("~") else b[1:]
                        if (neg_a in p_set and c_norm == b) or (neg_b in p_set and c_norm == a):
                            return f"**Regra Identificada:** Silogismo Disjuntivo (SD)\n\n" \
                                   f"**Explicação:** Havendo uma disjunção `{a}|{b}` (onde pelo menos uma alternativa é verdadeira) e sabendo " \
                                   f"que uma delas foi eliminada por sua negação, conclui-se necessariamente a outra."

            # 5. ADIÇÃO (A) -> A => A|B
            if "|" in c_norm:
                partes_c = c_norm.split("|")
                if any(p in partes_c for p in p_norm):
                    return f"**Regra Identificada:** Adição (A)\n\n" \
                           f"**Explicação:** Como uma das propriedades já é verdadeira pelas premissas, a introdução de uma disjunção " \
                           f"('OU') com qualquer outra variável mantém o argumento inteiramente válido."

            # 6. REGRAS DO BICONDICIONAL (BIC) -> A<->B => A->B (ou vice-versa)
            for p in p_norm:
                if "<->" in p:
                    a, b = p.split("<->", 1)
                    if c_norm in (f"{a}->{b}", f"{b}->{a}"):
                        return f"**Regra Identificada:** Regras do Bicondicional (BIC)\n\n" \
                               f"**Explicação:** A dupla implicação `{a}<->{b}` significa que tanto `{a}->{b}` quanto `{b}->{a}` são verdadeiros."

            if "->" in c_norm and len(p_norm) >= 2:
                for p1 in p_norm:
                    if "->" in p1 and "<->" not in p1:
                        a, b = p1.split("->", 1)
                        if f"{b}->{a}" in p_set and c_norm == f"{a}<->{b}":
                            return f"**Regra Identificada:** Regras do Bicondicional (BIC)\n\n" \
                                   f"**Explicação:** Havendo a implicação mútua nas premissas, conclui-se a equivalência lógica exata `{a}<->{b}`."

            # 7. SIMPLIFICAÇÃO (S) -> A&B => A
            for p in p_norm:
                if "&" in p:
                    partes_p = p.split("&")
                    if c_norm in partes_p:
                        return f"**Regra Identificada:** Simplificação (S)\n\n" \
                               f"**Explicação:** Uma conjunção (`{p}`) exige que ambas as partes sejam simultaneamente verdadeiras, sendo legítimo extrair qualquer componente."

            # 8. SIMPLIFICAÇÃO DISJUNTIVA (S+)
            for p in p_norm:
                if "|" in p and p.split("|")[0] == p.split("|")[1] and c_norm == p.split("|")[0]:
                    return f"**Regra Identificada:** Simplificação Disjuntiva (S+)\n\n" \
                           f"**Explicação:** A disjunção de uma proposição com ela mesma reduz-se logicamente à própria proposição única."

            disjuncoes = [p for p in p_norm if "|" in p]
            if len(disjuncoes) >= 2:
                for d1 in disjuncoes:
                    partes1 = d1.split("|")
                    if len(partes1) == 2:
                        a1, b1 = partes1[0], partes1[1]
                        for d2 in disjuncoes:
                            if d1 != d2:
                                partes2 = d2.split("|")
                                if len(partes2) == 2:
                                    a2, b2 = partes2[0], partes2[1]
                                    neg_b1 = f"~{b1}" if not b1.startswith("~") else b1[1:]
                                    neg_a1 = f"~{a1}" if not a1.startswith("~") else a1[1:]
                                    if a1 == a2 and (b2 == neg_b1 or b1 == f"~{b2}" or b2 == f"~{b1}") and c_norm == a1:
                                        return f"**Regra Identificada:** Simplificação Disjuntiva (S+)\n\n" \
                                               f"**Explicação:** Temos um caso de simplificação por eliminação de literais opostos. Se `{a1}` é pareado de forma disjuntiva tanto com uma variável quanto com a negação exata dela, a variável oposta se anula, restando apenas a afirmação de `{a1}`."
                                    if b1 == b2 and (a2 == neg_a1 or a1 == f"~{a2}" or a2 == f"~{a1}") and c_norm == b1:
                                        return f"**Regra Identificada:** Simplificação Disjuntiva (S+)\n\n" \
                                               f"**Explicação:** Simplificação por eliminação de contradição de termos adjacentes. Sobra apenas o termo comum `{b1}`."
            if len(p_norm) >= 2:
                for p1 in p_norm:
                    if "&" in p1:
                        partes = p1.split("&")
                        if "->" in partes[0] and "->" in partes[1]:
                            a, b1 = partes[0].split("->", 1)
                            c, b2 = partes[1].split("->", 1)
                            if b1 == b2 and b1 == c_norm and (f"{a}|{c}" in p_set or f"{c}|{a}" in p_set):
                                return f"**Regra Identificada:** Simplificação Disjuntiva (S+)\n\n" \
                                       f"**Explicação:** Se ambos os caminhos alternativos levam ao mesmo resultado, o resultado ocorrerá de qualquer forma."

            # 9. UNIÃO (U) -> A, B => A&B
            if "&" in c_norm:
                partes_c = c_norm.split("&")
                if len(partes_c) == 2:
                    c1, c2 = partes_c[0], partes_c[1]
                    if (c1 in p_set or any(c1 in p and "&" in p for p in p_norm)) and \
                       (c2 in p_set or any(c2 in p and "&" in p for p in p_norm)):
                        return f"**Regra Identificada:** União (U)\n\n" \
                               f"**Explicação:** Se duas premissas são verdadeiras isoladamente ou estão provadas no sistema, elas podem ser unidas através do conectivo 'E' (`&`)."

            return "**Regra Identificada:** Dedução Válida Geral.\n\n" \
                   "**Explicação:** O argumento foi validado com sucesso através da matriz da tabela-verdade, embora represente uma composição complexa de passos dedutivos."
        else:
            # Tratamento para Falácias
            for p in p_norm:
                if "->" in p and "<->" not in p:
                    antecedente, consequente = p.split("->", 1)
                    if consequente in p_set and c_norm == antecedente:
                        return f"**Falácia Identificada:** Afirmação do Consequente.\n\n" \
                               f"**Por que é inválido?** Mesmo que `{antecedente} -> {consequente}` seja verdade, saber que o efeito `{consequente}` ocorreu não garante que ele foi desencadeado especificamente por `{antecedente}`."
                    neg_antecedente = f"~{antecedente}" if not antecedente.startswith("~") else antecedente[1:]
                    neg_consequente = f"~{consequente}" if not consequente.startswith("~") else consequente[1:]
                    if neg_antecedente in p_set and c_norm == neg_consequente:
                        return f"**Falácia Identificada:** Negação do Antecedente.\n\n" \
                               f"**Por que é inválido?** A ausência da causa primitiva `{neg_antecedente}` não impede que o efeito ocorra por outras vias não mapeadas."

            return "**Falácia Identificada:** Falácia Lógica Geral.\n\n" \
                   "**Por que é inválido?** A tabela-verdade provou computacionalmente a existência de linhas inconsistentes onde as premissas são Verdadeiras e a conclusão é Falsa."

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
* *Separe premissas por **vírgulas** em uma mesma entrada (ex: `p + r, p + r'`).*
""")

st.sidebar.markdown("---")

st.sidebar.header("📜 Guia de Regras de Inferência")
with st.sidebar.expander("Modus Ponens (MP)"):
    st.markdown("**Premissas:** `p -> q, p` \n\n**Conclusão:** `q`")
with st.sidebar.expander("Modus Tollens (MT)"):
    st.markdown("**Premissas:** `p -> q, q'` \n\n**Conclusão:** `p'`")
with st.sidebar.expander("Silogismo Hipotético (SH)"):
    st.markdown("**Premissas:** `p -> q, q -> r` \n\n**Conclusão:** `p -> r` *(ou `q -> r`)*")
with st.sidebar.expander("Silogismo Disjuntivo (SD)"):
    st.markdown("**Premissas:** `p + q, p'` \n\n**Conclusão:** `q`")
with st.sidebar.expander("Adição (A)"):
    st.markdown("**Premissas:** `p` \n\n**Conclusão:** `p + q`")
with st.sidebar.expander("Regras do Bicondicional (BIC)"):
    st.markdown("**Premissas:** `p <-> q` \n\n**Conclusão:** `p -> q` \n\n*Ou vice-versa (`p->q, q->p` gerando `p<->q`)*")
with st.sidebar.expander("Simplificação (S)"):
    st.markdown("**Premissas:** `p . q` \n\n**Conclusão:** `p`")
with st.sidebar.expander("Simplificação Disjuntiva (S+)"):
    st.markdown("**Premissas:** `p + r, p + r'` \n\n**Conclusão:** `p` \n\n*Aceita também Idempotência (`p + p` gerando `p`)*")
with st.sidebar.expander("União (U)"):
    st.markdown("**Premissas:** `p, q` \n\n**Conclusão:** `p . q`")


# --- CORPO PRINCIPAL DOS MÓDULOS ---
motor = MotorLogico()

# ADICIONADO O MÓDULO A EXPLICITAMENTE NAS ABAS ABAIXO
tab_interpretador, tab_equiv, tab_inferencia = st.tabs([
    "Módulo A: Interpretador de Expressões",
    "Módulo B: Provador de Equivalência",
    "Módulo C: Motor de Inferência (Validador)"
])

# --- MÓDULO A (NOVO) ---
with tab_interpretador:
    st.header("Interpretador e Normalizador de Fórmulas")
    st.write("Digite uma expressão para ver como o Motor realiza a análise léxica, normalização das variáveis e a tradução para código Python computável.")
    
    expressao_teste = st.text_input("Insira uma expressão lógica para visualização da tradução:", value="~A -> (B . c)'")
    
    if expressao_teste:
        try:
            expr_normalizada = motor.normalizar_expressao(expressao_teste)
            expr_python = motor.preparar_expressao(expressao_teste)
            variaveis_detectadas = motor.extrair_variaveis([expressao_teste])
            
            col_a1, col_a2 = st.columns(2)
            with col_a1:
                st.info(f"**Expressão Padronizada (Motor):** `{expr_normalizada}`")
                st.success(f"**Tradução Interna Python (`eval`):** `{expr_python}`")
            with col_a2:
                st.metric("Variáveis Identificadas", ", ".join(variaveis_detectadas) if variaveis_detectadas else "Nenhuma")
        except Exception as e:
            st.error(f"Erro ao processar expressão no interpretador: {e}")

# --- MÓDULO B ---
with tab_equiv:
    st.header("Verificador de Equivalência Lógica")
    st.write("Insira duas expressões para verificar se elas possuem tabelas-verdade idênticas (Ex: Leis de De Morgan, Contrapositiva).")
    
    col1, col2 = st.columns(2)
    with col1:
        e1 = st.text_input("Primeira Expressão (Entrada 1):", value="A -> B")
    with col2:
        e2 = st.text_input("Segunda Expressão (Entrada 2):", value="~B -> ~A")

    if st.button("Calcular Equivalência", key="btn_equiv"):
        if e1 and e2:
            try:
                df_resultado, sao_equivalentes = motor.processar_equivalencia(e1, e2)
                if sao_equivalentes:
                    st.success("### 🟩 Resposta: Expressões LOGICAMENTE EQUIVALENTES (Contrapositiva Válida)")
                else:
                    st.error("### 🟥 Resposta: Expressões NÃO SÃO EQUIVALENTES")
                st.write("#### Tabela-Verdade Gerada:")
                st.dataframe(df_resultado, use_container_width=True)
            except Exception as e:
                st.error(f"Erro ao processar: {e}")
        else:
            st.warning("Por favor, preencha ambas as expressões.")

# --- MÓDULO C ---
with tab_inferencia:
    st.header("Validador de Argumentos Lógicos com Explicação Didática")
    st.write("Defina um conjunto de premissas e veja se a conclusão decorre logicamente delas.")
    st.caption("💡 **Dica:** Você pode abrir o Guia de Regras ao lado esquerdo para copiar os formatos exatos.")

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
    
    defaults_premissas = ["p + r, p + r'"]
    
    for i in range(st.session_state.num_premissas):
        val_default = defaults_premissas[i] if i < len(defaults_premissas) else ""
        p_in = st.text_input(f"Entrada {i+1}:", value=val_default, key=f"premissa_{i}")
        if p_in.strip():
            premissas_brutas.append(p_in)

    st.write("#### Conclusão:")
    conclusao_input = st.text_input("Conclusão do Argumento:", value="p", key="conclusao")

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
