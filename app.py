import streamlit as st
import pandas as pd

st.set_page_config(page_title="Calculadora IBS / CBS", layout="wide")

st.title("📊 Simulador de Impacto Tributário: IBS & CBS")
st.markdown("Calcule o débito, crédito e valor líquido a recolher no novo modelo de IVA Dual.")

# Sidebar - Parâmetros
st.sidebar.header("Parâmetros da Operação")
faturamento = st.sidebar.number_input("Faturamento Bruto (R$)", min_value=0.0, value=100000.0, step=1000.0)
compras = st.sidebar.number_input("Insumos/Aquisições com Crédito (R$)", min_value=0.0, value=40000.0, step=1000.0)

st.sidebar.header("Alíquotas Estimadas (%)")
aliq_cbs = st.sidebar.number_input("Alíquota CBS (%)", min_value=0.0, value=8.8, step=0.1) / 100
aliq_ibs = st.sidebar.number_input("Alíquota IBS (%)", min_value=0.0, value=17.7, step=0.1) / 100

# Cálculos
cbs_debito = faturamento * aliq_cbs
cbs_credito = compras * aliq_cbs
cbs_liquido = max(0.0, cbs_debito - cbs_credito)

ibs_debito = faturamento * aliq_ibs
ibs_credito = compras * aliq_ibs
ibs_liquido = max(0.0, ibs_debito - ibs_credito)

total_recolher = cbs_liquido + ibs_liquido
carga_efetiva = (total_recolher / faturamento * 100) if faturamento > 0 else 0

# Exibição de Resultados
col1, col2, col3, col4 = st.columns(4)
col1.metric("CBS a Recolher", f"R$ {cbs_liquido:,.2f}")
col2.metric("IBS a Recolher", f"R$ {ibs_liquido:,.2f}")
col3.metric("Total de Imposto Líquido", f"R$ {total_recolher:,.2f}")
col4.metric("Carga Efetiva", f"{carga_efetiva:.2f}%")

st.divider()

# Detalhamento em Tabela
st.subheader("📋 Resumo da Apuração")
df_resultado = pd.DataFrame({
    "Tributo": ["CBS (Federal)", "IBS (Estadual/Municipal)", "Total (IVA Dual)"],
    "Débito (Vendas)": [cbs_debito, ibs_debito, cbs_debito + ibs_debito],
    "Crédito (Compras)": [cbs_credito, ibs_credito, cbs_credito + ibs_credito],
    "Imposto Líquido": [cbs_liquido, ibs_liquido, total_recolher]
})

st.dataframe(df_resultado.style.format({
    "Débito (Vendas)": "R$ {:,.2f}",
    "Crédito (Compras)": "R$ {:,.2f}",
    "Imposto Líquido": "R$ {:,.2f}"
}), use_container_width=True)
