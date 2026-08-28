import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET

st.set_page_config(page_title="Calculadora IBS/CBS - Visual Planilha", layout="wide")

# Estilização inspirada nas cores da planilha (Azul, Laranja e Verde)
st.markdown("""
    <style>
    /* Estilo para Títulos */
    .title-banner {
        background-color: #1F3864;
        color: white;
        padding: 15px;
        border-radius: 6px;
        text-align: center;
        font-weight: bold;
        font-size: 24px;
        margin-bottom: 20px;
    }
    
    /* Cartões de Impostos (Laranja) */
    div[data-testid="stMetric"] {
        background-color: #FFF2CC;
        border-left: 5px solid #C65911;
        padding: 10px;
        border-radius: 4px;
    }
    
    /* Customização do DataFrame / Tabelas */
    .stDataFrame {
        border: 1px solid #1F3864;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="title-banner">Cálculo Base IBS/CBS - Processador de XML</div>', unsafe_allow_html=True)

# Mapeamento IBGE -> UF
IBGE_UF = {
    '11': 'RO', '12': 'AC', '13': 'AM', '14': 'RR', '15': 'PA', '16': 'AP', '17': 'TO',
    '21': 'MA', '22': 'PI', '23': 'CE', '24': 'RN', '25': 'PB', '26': 'PE', '27': 'AL',
    '28': 'SE', '29': 'BA', '31': 'MG', '32': 'ES', '33': 'RJ', '35': 'SP', '41': 'PR',
    '42': 'SC', '43': 'RS', '50': 'MS', '51': 'MT', '52': 'GO', '53': 'DF'
}

ALIQ_CBS_FIXA = 0.009  # 0,9%
ALIQ_IBS_FIXA = 0.001  # 0,1%

uploaded_files = st.file_uploader("Selecione os arquivos XML (NF-e, NFC-e ou NFS-e)", type=["xml"], accept_multiple_files=True)

def parse_xml_flex(xml_file):
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        def find_num_total(tag_names):
            for elem in root.iter():
                clean_tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if clean_tag in tag_names and elem.text:
                    try:
                        return float(elem.text)
                    except ValueError:
                        pass
            return 0.0

        def find_num_sum_items(tag_names):
            total = 0.0
            found = False
            for elem in root.iter():
                clean_tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if clean_tag in tag_names and elem.text:
                    try:
                        total += float(elem.text)
                        found = True
                    except ValueError:
                        pass
            return total if found else 0.0

        def get_uf_destino():
            for dest in root.iter():
                clean_tag = dest.tag.split('}')[-1] if '}' in dest.tag else dest.tag
                if clean_tag == 'dest':
                    for elem in dest.iter():
                        sub_tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                        if sub_tag == 'UF' and elem.text:
                            return str(elem.text).strip()
                        if sub_tag in ['cMun', 'CodigoMunicipio'] and elem.text and len(str(elem.text)) >= 2:
                            return IBGE_UF.get(str(elem.text)[:2], "N/A")
            
            for elem in root.iter():
                clean_tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if clean_tag in ['UF', 'uf'] and elem.text:
                    return str(elem.text).strip()
            return "N/A"

        uf_destino = get_uf_destino()

        v_nf = find_num_total(['vNF', 'ValorLiquidoNfse', 'vServicos', 'ValorServicos', 'vTotal'])
        if v_nf == 0.0: v_nf = find_num_total(['vProd'])

        v_frete = find_num_total(['vFrete', 'ValorFrete', 'vFreteTot'])
        if v_frete == 0.0: v_frete = find_num_sum_items(['vFrete'])

        v_pis = find_num_total(['vPIS', 'ValorPis', 'Pis'])
        if v_pis == 0.0: v_pis = find_num_sum_items(['vPIS'])

        v_cofins = find_num_total(['vCOFINS', 'ValorCofins', 'Cofins'])
        if v_cofins == 0.0: v_cofins = find_num_sum_items(['vCOFINS'])

        v_icms = find_num_total(['vICMS'])
        if v_icms == 0.0: v_icms = find_num_sum_items(['vICMS'])

        v_iss = find_num_total(['vISS', 'ValorIss', 'ValorIssRetido', 'vIss'])
        if v_iss == 0.0: v_iss = find_num_sum_items(['vISS'])

        v_ipi = find_num_total(['vIPI', 'ValorIpi'])
        if v_ipi == 0.0: v_ipi = find_num_sum_items(['vIPI'])

        total_impostos = v_pis + v_cofins + v_icms + v_iss + v_ipi
        base_calculo = max(0.0, v_nf - total_impostos)
        
        cbs_estimado = base_calculo * ALIQ_CBS_FIXA
        ibs_estimado = base_calculo * ALIQ_IBS_FIXA

        return {
            "Nome do Arquivo": xml_file.name,
            "UF Destino": uf_destino,
            "Valor Total NF (R$)": v_nf,
            "Frete (R$)": v_frete,
            "PIS (R$)": v_pis,
            "COFINS (R$)": v_cofins,
            "ICMS (R$)": v_icms,
            "ISS (R$)": v_iss,
            "IPI (R$)": v_ipi,
            "Soma Impostos (R$)": total_impostos,
            "Base IBS/CBS (R$)": base_calculo,
            "CBS (0.9%) (R$)": cbs_estimado,
            "IBS (0.1%) (R$)": ibs_estimado
        }
    except Exception as e:
        st.error(f"Erro ao processar {xml_file.name}: {e}")
        return None

if uploaded_files:
    dados = [res for f in uploaded_files if (res := parse_xml_flex(f))]
            
    if dados:
        df = pd.DataFrame(dados)
        
        st.sidebar.info(f"📁 {len(dados)} nota(s) processada(s).\n- CBS: **0,9%**\n- IBS: **0,1%**")
        
        # Seção Azul - Valores e Totais
        st.markdown("### 🔷 Valores Totais & Frete")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Valor Total NFs", f"R$ {df['Valor Total NF (R$)'].sum():,.2f}")
        c2.metric("Total Frete", f"R$ {df['Frete (R$)'].sum():,.2f}")
        c3.metric("Base Líquida IBS/CBS", f"R$ {df['Base IBS/CBS (R$)'].sum():,.2f}")
        c4.metric("CBS Total (0,9%)", f"R$ {df['CBS (0.9%) (R$)'].sum():,.2f}")
        c5.metric("IBS Total (0,1%)", f"R$ {df['IBS (0.1%) (R$)'].sum():,.2f}")

        st.divider()

        # Seção Laranja - Impostos Atual / Deduções
        st.markdown("### 🔶 Impostos Dedução (PIS, COFINS, ICMS, ISS, IPI)")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total PIS", f"R$ {df['PIS (R$)'].sum():,.2f}")
        m2.metric("Total COFINS", f"R$ {df['COFINS (R$)'].sum():,.2f}")
        m3.metric("Total ICMS", f"R$ {df['ICMS (R$)'].sum():,.2f}")
        m4.metric("Total ISS", f"R$ {df['ISS (R$)'].sum():,.2f}")
        m5.metric("Total IPI", f"R$ {df['IPI (R$)'].sum():,.2f}")

        st.divider()

        # Função de formatação de cores nas tabelas
        def style_dataframe(dataframe):
            return dataframe.style.format({
                "Valor Total NF (R$)": "R$ {:,.2f}",
                "Frete (R$)": "R$ {:,.2f}",
                "PIS (R$)": "R$ {:,.2f}",
                "COFINS (R$)": "R$ {:,.2f}",
                "ICMS (R$)": "R$ {:,.2f}",
                "ISS (R$)": "R$ {:,.2f}",
                "IPI (R$)": "R$ {:,.2f}",
                "Soma Impostos (R$)": "R$ {:,.2f}",
                "Base IBS/CBS (R$)": "R$ {:,.2f}",
                "CBS (0.9%) (R$)": "R$ {:,.2f}",
                "IBS (0.1%) (R$)": "R$ {:,.2f}"
            }).set_properties(**{
                'background-color': '#F2F2F2',
                'color': '#1F3864',
                'border-color': '#D9D9D9'
            })

        st.markdown("### 📋 Detalhamento Individual por Nota Fiscal")
        st.dataframe(style_dataframe(df), use_container_width=True)

        st.divider()

        st.markdown("### 🟢 Consolidação por UF de Destino")
        df_uf = df.groupby("UF Destino").agg({
            "Valor Total NF (R$)": "sum",
            "Frete (R$)": "sum",
            "PIS (R$)": "sum",
            "COFINS (R$)": "sum",
            "ICMS (R$)": "sum",
            "ISS (R$)": "sum",
            "IPI (R$)": "sum",
            "Soma Impostos (R$)": "sum",
            "Base IBS/CBS (R$)": "sum",
            "CBS (0.9%) (R$)": "sum",
            "IBS (0.1%) (R$)": "sum"
        }).reset_index()

        st.dataframe(style_dataframe(df_uf), use_container_width=True)
