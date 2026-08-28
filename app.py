import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET

st.set_page_config(page_title="Calculadora IBS/CBS - Impostos Discriminados", layout="wide")

st.title("📄 Processador de NF-e e NFS-e: Apuração Discriminada")
st.markdown("Visualização individual de cada imposto (PIS, COFINS, ICMS, ISS, IPI) e cálculo da base líquida para IBS/CBS.")

# Dicionário de Mapeamento de Código IBGE -> UF
IBGE_UF = {
    '11': 'RO', '12': 'AC', '13': 'AM', '14': 'RR', '15': 'PA', '16': 'AP', '17': 'TO',
    '21': 'MA', '22': 'PI', '23': 'CE', '24': 'RN', '25': 'PB', '26': 'PE', '27': 'AL',
    '28': 'SE', '29': 'BA', '31': 'MG', '32': 'ES', '33': 'RJ', '35': 'SP', '41': 'PR',
    '42': 'SC', '43': 'RS', '50': 'MS', '51': 'MT', '52': 'GO', '53': 'DF'
}

# Sidebar - Configurações de Alíquotas
st.sidebar.header("⚙️ Alíquotas Estimadas (%)")
aliq_cbs = st.sidebar.number_input("Alíquota CBS (%)", min_value=0.0, value=8.8, step=0.1) / 100
aliq_ibs = st.sidebar.number_input("Alíquota IBS (%)", min_value=0.0, value=17.7, step=0.1) / 100

uploaded_files = st.file_uploader("Selecione os arquivos XML (NF-e, NFC-e ou NFS-e)", type=["xml"], accept_multiple_files=True)

def parse_xml_flex(xml_file):
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        def find_num(tag_names):
            for elem in root.iter():
                clean_tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if clean_tag in tag_names and elem.text:
                    try:
                        return float(elem.text)
                    except ValueError:
                        pass
            return 0.0

        def find_str(tag_names):
            for elem in root.iter():
                clean_tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if clean_tag in tag_names and elem.text:
                    return str(elem.text).strip()
            return "N/A"

        # 1. Identificação do Estado (UF)
        uf = find_str(['UF', 'uf'])
        if uf == "N/A" or len(uf) != 2:
            c_mun = find_str(['cMun', 'cMunFG', 'CodigoMunicipio'])
            if c_mun != "N/A" and len(c_mun) >= 2:
                uf = IBGE_UF.get(c_mun[:2], "N/A")

        # 2. Valor Total da Nota Fiscal
        v_nf = find_num(['vNF', 'ValorLiquidoNfse', 'vServicos', 'ValorServicos', 'vTotal'])
        if v_nf == 0.0:
            v_nf = find_num(['vProd'])

        # 3. Leitura dos Impostos Individuais
        v_pis = find_num(['vPIS', 'ValorPis', 'Pis'])
        v_cofins = find_num(['vCOFINS', 'ValorCofins', 'Cofins'])
        v_icms = find_num(['vICMS'])
        v_iss = find_num(['vISS', 'ValorIss', 'ValorIssRetido', 'vIss'])
        v_ipi = find_num(['vIPI', 'ValorIpi'])

        total_impostos = v_pis + v_cofins + v_icms + v_iss + v_ipi
        
        # 4. Base de Cálculo do IBS/CBS
        base_calculo = max(0.0, v_nf - total_impostos)
        
        cbs_estimado = base_calculo * aliq_cbs
        ibs_estimado = base_calculo * aliq_ibs
        total_iva = cbs_estimado + ibs_estimado

        return {
            "Arquivo": xml_file.name,
            "UF": uf,
            "Valor Total NF (R$)": v_nf,
            "PIS (R$)": v_pis,
            "COFINS (R$)": v_cofins,
            "ICMS (R$)": v_icms,
            "ISS (R$)": v_iss,
            "IPI (R$)": v_ipi,
            "Soma Impostos (R$)": total_impostos,
            "Base IBS/CBS (R$)": base_calculo,
            "CBS Estimado (R$)": cbs_estimado,
            "IBS Estimado (R$)": ibs_estimado,
            "Total IBS + CBS (R$)": total_iva
        }
    except Exception as e:
        st.error(f"Erro ao processar {xml_file.name}: {e}")
        return None

if uploaded_files:
    dados = [res for f in uploaded_files if (res := parse_xml_flex(f))]
    if dados:
        df = pd.DataFrame(dados)
        
        # Cartões de Visão Geral dos Impostos
        st.subheader("📌 Totais Individuais por Imposto")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total PIS", f"R$ {df['PIS (R$)'].sum():,.2f}")
        m2.metric("Total COFINS", f"R$ {df['COFINS (R$)'].sum():,.2f}")
        m3.metric("Total ICMS", f"R$ {df['ICMS (R$)'].sum():,.2f}")
        m4.metric("Total ISS", f"R$ {df['ISS (R$)'].sum():,.2f}")
        m5.metric("Total IPI", f"R$ {df['IPI (R$)'].sum():,.2f}")

        st.divider()

        # Resumo dos IVA
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Valor Total NFs", f"R$ {df['Valor Total NF (R$)'].sum():,.2f}")
        c2.metric("Soma de Todos Impostos", f"R$ {df['Soma Impostos (R$)'].sum():,.2f}")
        c3.metric("Base Líquida IBS/CBS", f"R$ {df['Base IBS/CBS (R$)'].sum():,.2f}")
        c4.metric("Total IBS + CBS Estimado", f"R$ {df['Total IBS + CBS (R$)'].sum():,.2f}")

        st.divider()

        # Tabela Agrupada por Estado (UF)
        st.subheader("📍 Impostos Discriminados por Estado (UF)")
        df_uf = df.groupby("UF").agg({
            "Valor Total NF (R$)": "sum",
            "PIS (R$)": "sum",
            "COFINS (R$)": "sum",
            "ICMS (R$)": "sum",
            "ISS (R$)": "sum",
            "IPI (R$)": "sum",
            "Soma Impostos (R$)": "sum",
            "Base IBS/CBS (R$)": "sum",
            "CBS Estimado (R$)": "sum",
            "IBS Estimado (R$)": "sum",
            "Total IBS + CBS (R$)": "sum"
        }).reset_index()

        st.dataframe(df_uf.style.format({
            "Valor Total NF (R$)": "R$ {:,.2f}",
            "PIS (R$)": "R$ {:,.2f}",
            "COFINS (R$)": "R$ {:,.2f}",
            "ICMS (R$)": "R$ {:,.2f}",
            "ISS (R$)": "R$ {:,.2f}",
            "IPI (R$)": "R$ {:,.2f}",
            "Soma Impostos (R$)": "R$ {:,.2f}",
            "Base IBS/CBS (R$)": "R$ {:,.2f}",
            "CBS Estimado (R$)": "R$ {:,.2f}",
            "IBS Estimado (R$)": "R$ {:,.2f}",
            "Total IBS + CBS (R$)": "R$ {:,.2f}"
        }), use_container_width=True)

        # Tabela Detalhada por Arquivo/Nota
        st.subheader("📋 Detalhamento Nota por Nota")
        st.dataframe(df.style.format({
            "Valor Total NF (R$)": "R$ {:,.2f}",
            "PIS (R$)": "R$ {:,.2f}",
            "COFINS (R$)": "R$ {:,.2f}",
            "ICMS (R$)": "R$ {:,.2f}",
            "ISS (R$)": "R$ {:,.2f}",
            "IPI (R$)": "R$ {:,.2f}",
            "Soma Impostos (R$)": "R$ {:,.2f}",
            "Base IBS/CBS (R$)": "R$ {:,.2f}",
            "CBS Estimado (R$)": "R$ {:,.2f}",
            "IBS Estimado (R$)": "R$ {:,.2f}",
            "Total IBS + CBS (R$)": "R$ {:,.2f}"
        }), use_container_width=True)
