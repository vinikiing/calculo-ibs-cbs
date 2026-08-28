import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET

st.set_page_config(page_title="Calculadora IBS/CBS - Leitor Universal", layout="wide")

# Estilização de Alto Contraste (compatível com Dark e Light Mode)
st.markdown("""
    <style>
    .title-banner {
        background-color: #1F3864;
        color: #FFFFFF !important;
        padding: 15px;
        border-radius: 6px;
        text-align: center;
        font-weight: bold;
        font-size: 24px;
        margin-bottom: 20px;
    }
    div[data-testid="stMetric"] {
        background-color: #FFF2CC !important;
        border-left: 6px solid #C65911 !important;
        padding: 10px !important;
        border-radius: 6px !important;
    }
    div[data-testid="stMetric"] label {
        color: #333333 !important;
        font-weight: bold !important;
        font-size: 12px !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #1F3864 !important;
        font-weight: bold !important;
        font-size: 19px !important;
    }
    .stDataFrame {
        border: 1px solid #1F3864 !important;
        border-radius: 6px !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="title-banner">Cálculo Base IBS/CBS - Processador Universal de XML</div>', unsafe_allow_html=True)

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
        # Lê o conteúdo bruto do arquivo XML
        content = xml_file.read()
        xml_file.seek(0)
        
        root = ET.fromstring(content)
        
        # Mapeamento profundo de todas as tags e valores numéricos do arquivo
        tag_dict = {}
        for elem in root.iter():
            clean_tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            if elem.text:
                txt = elem.text.strip()
                # Tratamento para formatos monetários brasileiros (ex: 1.500,50 -> 1500.50)
                if ',' in txt:
                    txt = txt.replace('.', '').replace(',', '.')
                try:
                    val = float(txt)
                    if clean_tag not in tag_dict:
                        tag_dict[clean_tag] = []
                    tag_dict[clean_tag].append(val)
                except ValueError:
                    pass

        # Função de busca inteligente de valores numéricos dentro do XML
        def get_val_flex(keywords):
            for tag, vals in tag_dict.items():
                tag_lower = tag.lower()
                for kw in keywords:
                    if kw.lower() in tag_lower:
                        valid_vals = [v for v in vals if v > 0]
                        if valid_vals:
                            return max(valid_vals)
            return 0.0

        # Busca da UF do Destinatário/Tomador no XML
        def get_uf_destino():
            for dest in root.iter():
                clean_tag = dest.tag.split('}')[-1] if '}' in dest.tag else dest.tag
                if clean_tag in ['dest', 'TomadorServico', 'Tomador', 'PrestadorServico', 'enderDest']:
                    for elem in dest.iter():
                        sub_tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                        if sub_tag in ['UF', 'uf'] and elem.text:
                            return str(elem.text).strip()
                        if sub_tag in ['cMun', 'CodigoMunicipio'] and elem.text and len(str(elem.text)) >= 2:
                            return IBGE_UF.get(str(elem.text)[:2], "N/A")
            
            for elem in root.iter():
                clean_tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if clean_tag in ['UF', 'uf'] and elem.text:
                    return str(elem.text).strip()
            return "N/A"

        uf_destino = get_uf_destino()

        # Leitura dos valores de dentro do conteúdo do XML
        v_nf = get_val_flex(['ValorServicos', 'vServicos', 'vLiq', 'vNF', 'vProd', 'vTotal', 'ValorTotal', 'ValorLiquidoNfse'])
        v_frete = get_val_flex(['vFrete', 'ValorFrete', 'frete'])
        v_pis = get_val_flex(['vPIS', 'ValorPis', 'Pis', 'PISRet'])
        v_cofins = get_val_flex(['vCOFINS', 'ValorCofins', 'Cofins', 'COFINSRet'])
        v_icms = get_val_flex(['vICMS', 'ValorIcms', 'vICMSDeson'])
        v_iss = get_val_flex(['vISS', 'ValorIss', 'ValorIssRetido', 'ISSRet'])
        v_ipi = get_val_flex(['vIPI', 'ValorIpi', 'Ipi'])
        v_ir = get_val_flex(['vIRRF', 'ValorIrrf', 'vIR', 'ValorIr', 'Irrf'])
        v_inss = get_val_flex(['vINSS', 'ValorInss', 'vRetPrev', 'Inss', 'Csll'])

        total_impostos = v_pis + v_cofins + v_icms + v_iss + v_ipi + v_ir + v_inss
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
            "IRRF (R$)": v_ir,
            "INSS (R$)": v_inss,
            "Soma Impostos (R$)": total_impostos,
            "Base IBS/CBS (R$)": base_calculo,
            "CBS (0.9%) (R$)": cbs_estimado,
            "IBS (0.1%) (R$)": ibs_estimado,
            "_debug_tags": tag_dict
        }
    except Exception as e:
        st.error(f"Erro ao ler o conteúdo do XML {xml_file.name}: {e}")
        return None

if uploaded_files:
    dados = [res for f in uploaded_files if (res := parse_xml_flex(f))]
            
    if dados:
        df = pd.DataFrame(dados)
        debug_info = {d["Nome do Arquivo"]: d.pop("_debug_tags") for d in dados if "_debug_tags" in d}
        
        st.sidebar.info(f"📁 **Status:** {len(dados)} nota(s) processada(s).\n- CBS: **0,9%**\n- IBS: **0,1%**")
        
        st.markdown("### 🔷 Totais da Operação & Base IBS/CBS")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Valor Total NFs", f"R$ {df['Valor Total NF (R$)'].sum():,.2f}")
        c2.metric("Total Frete", f"R$ {df['Frete (R$)'].sum():,.2f}")
        c3.metric("Base Líquida IBS/CBS", f"R$ {df['Base IBS/CBS (R$)'].sum():,.2f}")
        c4.metric("CBS Total (0,9%)", f"R$ {df['CBS (0.9%) (R$)'].sum():,.2f}")
        c5.metric("IBS Total (0,1%)", f"R$ {df['IBS (0.1%) (R$)'].sum():,.2f}")

        st.divider()

        st.markdown("### 🔶 Impostos e Retenções Deduzidas")
        m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
        m1.metric("PIS", f"R$ {df['PIS (R$)'].sum():,.2f}")
        m2.metric("COFINS", f"R$ {df['COFINS (R$)'].sum():,.2f}")
        m3.metric("ICMS", f"R$ {df['ICMS (R$)'].sum():,.2f}")
        m4.metric("ISS", f"R$ {df['ISS (R$)'].sum():,.2f}")
        m5.metric("IPI", f"R$ {df['IPI (R$)'].sum():,.2f}")
        m6.metric("IRRF", f"R$ {df['IRRF (R$)'].sum():,.2f}")
        m7.metric("INSS", f"R$ {df['INSS (R$)'].sum():,.2f}")

        st.divider()

        st.markdown("### 📋 Detalhamento Individual por Nota Fiscal")
        st.dataframe(df.style.format({
            "Valor Total NF (R$)": "R$ {:,.2f}",
            "Frete (R$)": "R$ {:,.2f}",
            "PIS (R$)": "R$ {:,.2f}",
            "COFINS (R$)": "R$ {:,.2f}",
            "ICMS (R$)": "R$ {:,.2f}",
            "ISS (R$)": "R$ {:,.2f}",
            "IPI (R$)": "R$ {:,.2f}",
            "IRRF (R$)": "R$ {:,.2f}",
            "INSS (R$)": "R$ {:,.2f}",
            "Soma Impostos (R$)": "R$ {:,.2f}",
            "Base IBS/CBS (R$)": "R$ {:,.2f}",
            "CBS (0.9%) (R$)": "R$ {:,.2f}",
            "IBS (0.1%) (R$)": "R$ {:,.2f}"
        }), use_container_width=True)

        st.divider()

        st.markdown("### 📍 Consolidação por UF de Destino")
        df_uf = df.groupby("UF Destino").agg({
            "Valor Total NF (R$)": "sum",
            "Frete (R$)": "sum",
            "PIS (R$)": "sum",
            "COFINS (R$)": "sum",
            "ICMS (R$)": "sum",
            "ISS (R$)": "sum",
            "IPI (R$)": "sum",
            "IRRF (R$)": "sum",
            "INSS (R$)": "sum",
            "Soma Impostos (R$)": "sum",
            "Base IBS/CBS (R$)": "sum",
            "CBS (0.9%) (R$)": "sum",
            "IBS (0.1%) (R$)": "sum"
        }).reset_index()

        st.dataframe(df_uf.style.format({
            "Valor Total NF (R$)": "R$ {:,.2f}",
            "Frete (R$)": "R$ {:,.2f}",
            "PIS (R$)": "R$ {:,.2f}",
            "COFINS (R$)": "R$ {:,.2f}",
            "ICMS (R$)": "R$ {:,.2f}",
            "ISS (R$)": "R$ {:,.2f}",
            "IPI (R$)": "R$ {:,.2f}",
            "IRRF (R$)": "R$ {:,.2f}",
            "INSS (R$)": "R$ {:,.2f}",
            "Soma Impostos (R$)": "R$ {:,.2f}",
            "Base IBS/CBS (R$)": "R$ {:,.2f}",
            "CBS (0.9%) (R$)": "R$ {:,.2f}",
            "IBS (0.1%) (R$)": "R$ {:,.2f}"
        }), use_container_width=True)

        # Diagnóstico de Tags do Conteúdo do XML
        with st.expander("🔍 Diagnóstico do Conteúdo do XML"):
            st.write("Abaixo estão todos os valores numéricos capturados do CONTEÚDO do XML:")
            st.json(debug_info)
