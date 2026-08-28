import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET

st.set_page_config(page_title="Calculadora IBS/CBS via XML (NF-e e NFS-e)", layout="wide")

st.title("📄 Processador de NF-e, NFC-e e NFS-e: Cálculo de IBS & CBS")
st.markdown("Faça o upload dos seus arquivos XML (Mercadorias ou Serviços) para calcular o IBS e a CBS.")

# Sidebar - Configurações de Alíquotas
st.sidebar.header("⚙️ Alíquotas Estimadas (%)")
aliq_cbs = st.sidebar.number_input("Alíquota CBS (%)", min_value=0.0, value=8.8, step=0.1) / 100
aliq_ibs = st.sidebar.number_input("Alíquota IBS (%)", min_value=0.0, value=17.7, step=0.1) / 100

uploaded_files = st.file_uploader("Selecione um ou mais arquivos XML", type=["xml"], accept_multiple_files=True)

def parse_xml_universal(xml_file):
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        # Função para buscar texto ignorando namespace
        def find_tag_text(root_node, tag_names):
            for elem in root_node.iter():
                # Remove o namespace da tag
                clean_tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if clean_tag in tag_names and elem.text:
                    try:
                        return float(elem.text)
                    except ValueError:
                        return elem.text
            return 0.0

        # Identificação de tipo: NF-e vs NFS-e
        root_tag = root.tag.split('}')[-1] if '}' in root.tag else root.tag
        
        v_prod = 0.0
        v_nf = 0.0
        v_pis = 0.0
        v_cofins = 0.0
        v_icms_iss = 0.0
        tipo_doc = "NF-e / NFC-e"

        # Leitura flexível para NFS-e (Padrões ABRASF, DSF, etc.)
        if "CompNfse" in root_tag or "Nfse" in root_tag or "ConsultarNfse" in root_tag:
            tipo_doc = "NFS-e (Serviço)"
            v_prod = find_tag_text(root, ['vServicos', 'ValorServicos', 'ValorLiquidoNfse', 'vBc'])
            v_nf = v_prod
            v_pis = find_tag_text(root, ['ValorPis', 'vPIS', 'Pis'])
            v_cofins = find_tag_text(root, ['ValorCofins', 'vCOFINS', 'Cofins'])
            v_icms_iss = find_tag_text(root, ['ValorIss', 'vISS', 'ValorIssRetido', 'vIss'])
        else:
            # Leitura para NF-e / NFC-e
            v_prod = find_tag_text(root, ['vProd'])
            v_nf = find_tag_text(root, ['vNF'])
            v_desc = find_tag_text(root, ['vDesc'])
            v_frete = find_tag_text(root, ['vFrete'])
            
            v_pis = find_tag_text(root, ['vPIS'])
            v_cofins = find_tag_text(root, ['vCOFINS'])
            v_icms_iss = find_tag_text(root, ['vICMS'])
            
            if v_prod == 0.0:
                v_prod = v_nf

        base_calculo = v_prod if v_prod > 0 else v_nf
        cbs_estimado = base_calculo * aliq_cbs
        ibs_estimado = base_calculo * aliq_ibs
        total_iva = cbs_estimado + ibs_estimado
        tributos_atuais = v_pis + v_cofins + v_icms_iss

        return {
            "Arquivo": xml_file.name,
            "Tipo": tipo_doc,
            "Valor Total (R$)": v_nf if v_nf > 0 else base_calculo,
            "Base de Cálculo (R$)": base_calculo,
            "PIS/COFINS Atual (R$)": v_pis + v_cofins,
            "ICMS/ISS Atual (R$)": v_icms_iss,
            "Tributos Atuais (R$)": tributos_atuais,
            "CBS Estimado (R$)": cbs_estimado,
            "IBS Estimado (R$)": ibs_estimado,
            "Total IBS/CBS (R$)": total_iva
        }
    except Exception as e:
        st.error(f"Erro ao processar {xml_file.name}: {e}")
        return None

if uploaded_files:
    dados_processados = []
    for file in uploaded_files:
        res = parse_xml_universal(file)
        if res:
            dados_processados.append(res)
            
    if dados_processados:
        df = pd.DataFrame(dados_processados)
        
        st.subheader("📊 Resumo dos XMLs Processados")
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
        
        st.subheader("📋 Tabela Detalhada")
        st.dataframe(df.style.format({
            "Valor Total (R$)": "R$ {:,.2f}",
            "Base de Cálculo (R$)": "R$ {:,.2f}",
            "PIS/COFINS Atual (R$)": "R$ {:,.2f}",
            "ICMS/ISS Atual (R$)": "R$ {:,.2f}",
            "Tributos Atuais (R$)": "R$ {:,.2f}",
            "CBS Estimado (R$)": "R$ {:,.2f}",
            "IBS Estimado (R$)": "R$ {:,.2f}",
            "Total IBS/CBS (R$)": "R$ {:,.2f}"
        }), use_container_width=True)
