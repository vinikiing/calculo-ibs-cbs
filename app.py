import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET

st.set_page_config(page_title="Calculadora IBS/CBS via XML", layout="wide")

st.title("📄 Processador de NFe/NFCe: Cálculo de IBS & CBS")
st.markdown("Faça o upload de arquivos XML de NF-e para calcular o IBS e a CBS automaticamente.")

# Sidebar - Configurações de Alíquotas
st.sidebar.header("⚙️ Alíquotas Estimadas (%)")
aliq_cbs = st.sidebar.number_input("Alíquota CBS (%)", min_value=0.0, value=8.8, step=0.1) / 100
aliq_ibs = st.sidebar.number_input("Alíquota IBS (%)", min_value=0.0, value=17.7, step=0.1) / 100

# Upload do Arquivo XML
uploaded_files = st.file_uploader("Selecione um ou mais arquivos XML de NF-e", type=["xml"], accept_multiple_files=True)

def parse_xml_nfe(xml_file):
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        # Namespace padrão da NFe
        ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
        
        # Leitura da Chave
        ch_nfe = root.find('.//nfe:infNFe', ns)
        if ch_nfe is None:
            ch_nfe = root.find('.//infNFe')
        
        chave = ch_nfe.attrib.get('Id', 'N/A').replace('NFe', '') if ch_nfe is not None else 'N/A'
        
        # Função auxiliar para extrair tags numéricas
        def get_val(path):
            node = root.find(f'.//{path}', ns)
            if node is None:
                node = root.find(f'.//{path}')
            return float(node.text) if node is not None and node.text else 0.0

        v_prod = get_val('nfe:vProd') or get_val('vProd')
        v_nf = get_val('nfe:vNF') or get_val('vNF')
        v_frete = get_val('nfe:vFrete') or get_val('vFrete')
        v_desc = get_val('nfe:vDesc') or get_val('vDesc')
        
        # Valores tributários legados para comparação
        v_pis = get_val('nfe:vPIS') or get_val('vPIS')
        v_cofins = get_val('nfe:vCOFINS') or get_val('vCOFINS')
        v_icms = get_val('nfe:vICMS') or get_val('vICMS')
        
        # Base de cálculo do IBS/CBS (Produtos - Descontos + Frete)
        base_calculo = v_prod - v_desc + v_frete
        if base_calculo <= 0:
            base_calculo = v_nf
            
        cbs_estimado = base_calculo * aliq_cbs
        ibs_estimado = base_calculo * aliq_ibs
        total_iva = cbs_estimado + ibs_estimado
        
        return {
            "Chave NFe": chave,
            "Valor Nota (R$)": v_nf,
            "Base de Cálculo (R$)": base_calculo,
            "PIS Atual (R$)": v_pis,
            "COFINS Atual (R$)": v_cofins,
            "ICMS Atual (R$)": v_icms,
            "Tributos Atuais (R$)": v_pis + v_cofins + v_icms,
            "CBS Estimado (R$)": cbs_estimado,
            "IBS Estimado (R$)": ibs_estimado,
            "Total IBS/CBS (R$)": total_iva
        }
    except Exception as e:
        st.error(f"Erro ao processar o arquivo {xml_file.name}: {e}")
        return None

if uploaded_files:
    dados_processados = []
    for file in uploaded_files:
        res = parse_xml_nfe(file)
        if res:
            dados_processados.append(res)
            
    if dados_processados:
        df = pd.DataFrame(dados_processados)
        
        st.subheader("📊 Totais Apurados das Notas Enviadas")
        tot_base = df["Base de Cálculo (R$)"].sum()
        tot_cbs = df["CBS Estimado (R$)"].sum()
        tot_ibs = df["IBS Estimado (R$)"].sum()
        tot_iva = df["Total IBS/CBS (R$)"].sum()
        tot_atual = df["Tributos Atuais (R$)"].sum()
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Base Total Processada", f"R$ {tot_base:,.2f}")
        c2.metric("CBS Total (Federal)", f"R$ {tot_cbs:,.2f}")
        c3.metric("IBS Total (Est./Mun.)", f"R$ {tot_ibs:,.2f}")
        c4.metric("Total IBS + CBS", f"R$ {tot_iva:,.2f}")
        
        st.divider()
        
        # Comparativo com o modelo antigo
        diff = tot_iva - tot_atual
        st.subheader("⚖️ Comparativo: Modelo Atual vs. Novo IVA Dual")
        col_comp1, col_comp2 = st.columns(2)
        col_comp1.metric("Impostos Atuais (PIS+COFINS+ICMS)", f"R$ {tot_atual:,.2f}")
        col_comp2.metric(
            "Variação Estimada de Carga", 
            f"R$ {diff:,.2f}", 
            delta=f"{(diff/tot_base*100):.2f}%" if tot_base > 0 else "0%"
        )
        
        st.subheader("📋 Detalhamento Nota a Nota")
        st.dataframe(df.style.format({
            "Valor Nota (R$)": "R$ {:,.2f}",
            "Base de Cálculo (R$)": "R$ {:,.2f}",
            "PIS Atual (R$)": "R$ {:,.2f}",
            "COFINS Atual (R$)": "R$ {:,.2f}",
            "ICMS Atual (R$)": "R$ {:,.2f}",
            "Tributos Atuais (R$)": "R$ {:,.2f}",
            "CBS Estimado (R$)": "R$ {:,.2f}",
            "IBS Estimado (R$)": "R$ {:,.2f}",
            "Total IBS/CBS (R$)": "R$ {:,.2f}"
        }), use_container_width=True)
