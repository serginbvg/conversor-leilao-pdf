import streamlit as st
import pandas as pd
import io
import os
import json
from extractor import extrair_lotes_de_pdf, formatar_lote_para_planilha, parse_descricao
from google_sheets import (
    obter_cliente_gspread,
    sobrepor_lotes_na_planilha,
    gravar_via_webhook,
    COLUNAS_PADRAO
)

st.set_page_config(
    page_title="Conversor de Leilão para Google Sheets",
    page_icon="🐂",
    layout="wide"
)

# Estilização
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1b5e20;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        color: #555;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🐂 Conversor de Leilão de Gado</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Extraia automaticamente os lotes do PDF do leilão e lance direto na sua planilha do Google Drive</div>', unsafe_allow_html=True)

# Barra lateral com métodos de integração
with st.sidebar:
    st.header("⚙️ Conexão com a Planilha")
    
    metodo = st.radio(
        "Como deseja conectar?",
        ["🔗 Webhook do Apps Script (Mais Fácil)", "🔑 Conta de Serviço (Google Cloud)"],
        index=0
    )

    webhook_url = ""
    creds_source = None
    spreadsheet_id = "1YN1TH_QlMCylMIvlKVM6mFt1NyQqfh-54JYbZS1S41A"
    gid_input = "673667983"

    if metodo == "🔗 Webhook do Apps Script (Mais Fácil)":
        st.markdown("**Como usar:** Cole a URL gerada pelo Apps Script da sua planilha:")
        webhook_url = st.text_input(
            "URL do Webhook (Google Apps Script)",
            placeholder="https://script.google.com/macros/s/.../exec",
            help="Cole a URL do App da Web gerada no menu Extensões > Apps Script da sua planilha"
        )
        with st.expander("❓ Como gerar essa URL em 1 minuto?"):
            st.markdown("""
            1. Abra sua planilha do Google.
            2. Vá em **Extensões** ➔ **Apps Script**.
            3. Cole o código fornecido.
            4. Clique em **Implantar** ➔ **Nova implantação** ➔ Tipo: **App da Web**.
            5. Defina: Quem tem acesso = *Qualquer pessoa*.
            6. Copie a URL gerada e cole aqui!
            """)

    else:
        spreadsheet_id = st.text_input(
            "ID da Planilha Google",
            value="1YN1TH_QlMCylMIvlKVM6mFt1NyQqfh-54JYbZS1S41A"
        )
        gid_input = st.text_input(
            "GID da Aba (opcional)",
            value="673667983"
        )
        if "gcp_service_account" in st.secrets:
            creds_source = dict(st.secrets["gcp_service_account"])
            st.success("✅ Credenciais ativas via Segredos da Nuvem")
        elif os.path.exists("credentials.json"):
            with open("credentials.json", "r", encoding="utf-8") as f:
                creds_source = json.load(f)
            st.success("✅ credentials.json detectado")
        else:
            uploaded_creds = st.file_uploader("Arquivo de Credenciais (.json)", type=["json"], key="creds_file")
            if uploaded_creds:
                try:
                    creds_source = json.load(uploaded_creds)
                    st.success("✅ Credenciais carregadas!")
                except Exception as e:
                    st.error(f"Erro ao ler JSON: {e}")

# Upload do PDF principal
uploaded_pdf = st.file_uploader(
    "📄 Selecione ou arraste o PDF do Leilão:",
    type=["pdf"],
    help="Envie o arquivo PDF com a relação dos lotes"
)

if uploaded_pdf is not None:
    with st.spinner("Lendo e interpretando os lotes do PDF..."):
        try:
            lotes_extraidos = extrair_lotes_de_pdf(uploaded_pdf)
        except Exception as e:
            st.error(f"Erro durante a leitura do PDF: {e}")
            lotes_extraidos = []

    if lotes_extraidos:
        df_lotes = pd.DataFrame(lotes_extraidos)

        df_lotes["QUANTIDADE_NUM"] = pd.to_numeric(df_lotes["QUANTIDADE"], errors="coerce").fillna(0).astype(int)
        total_lotes = len(df_lotes)
        total_cabecas = int(df_lotes["QUANTIDADE_NUM"].sum())
        
        total_machos = int(df_lotes[df_lotes["SX_ORIGINAL"] == "M"]["QUANTIDADE_NUM"].sum())
        total_femeas = int(df_lotes[df_lotes["SX_ORIGINAL"] == "F"]["QUANTIDADE_NUM"].sum())

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📦 Total de Lotes", f"{total_lotes}")
        col2.metric("🐂 Total de Cabeças", f"{total_cabecas}")
        col3.metric("♂️ Machos", f"{total_machos}")
        col4.metric("♀️ Fêmeas", f"{total_femeas}")

        st.markdown("### 📋 Conferência dos Lotes Extraídos")
        st.caption("Você pode conferir os dados ou fazer correções manuais na tabela abaixo antes de enviar para a planilha.")

        colunas_exibicao = ["LOTE", "QUANTIDADE", "SEXO", "raca", "MESES", "KG", "LOCAL", "observacao"]
        df_exibicao = df_lotes[colunas_exibicao]

        df_editado = st.data_editor(
            df_exibicao,
            use_container_width=True,
            num_rows="dynamic",
            key="editor_lotes"
        )

        st.markdown("---")

        col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])

        with col_btn1:
            if st.button("🚀 Gravar e Sobrepor na Planilha Google", type="primary", use_container_width=True):
                dados_finais = df_editado.to_dict(orient="records")
                
                # Opção 1: Webhook (Sem JSON e sem Google Cloud)
                if metodo.startswith("🔗"):
                    if not webhook_url:
                        st.error("⚠️ Cole a URL do Webhook na barra lateral à esquerda.")
                    else:
                        with st.spinner("Enviando dados diretamente para a planilha via Webhook..."):
                            try:
                                res = gravar_via_webhook(webhook_url, dados_finais)
                                st.success(f"🎉 Sucesso! {len(dados_finais)} lotes foram sobrepostos na sua planilha!")
                                st.markdown(f"👉 [**Abrir Planilha Atualizada**](https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit)")
                            except Exception as e:
                                st.error(f"Erro ao enviar para o Webhook: {e}")

                # Opção 2: Conta de Serviço
                else:
                    if not creds_source:
                        st.error("⚠️ Carregue o arquivo de credenciais na barra lateral.")
                    else:
                        with st.spinner("Conectando ao Google Sheets e atualizando dados..."):
                            try:
                                cliente = obter_cliente_gspread(creds_source)
                                gid_val = int(gid_input.strip()) if gid_input.strip().isdigit() else None
                                resultado = sobrepor_lotes_na_planilha(cliente, spreadsheet_id.strip(), dados_finais, gid=gid_val)
                                st.success(f"🎉 Sucesso! {resultado['total_linhas']} lotes foram sobrepostos na aba '{resultado['aba']}' da sua planilha!")
                                link_planilha = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id.strip()}/edit"
                                if gid_val:
                                    link_planilha += f"#gid={gid_val}"
                                st.markdown(f"👉 [**Abrir Planilha Atualizada**]({link_planilha})")
                            except Exception as e:
                                st.error(f"Erro ao gravar na planilha: {e}")

        with col_btn2:
            buffer_excel = io.BytesIO()
            with pd.ExcelWriter(buffer_excel, engine="openpyxl") as writer:
                df_editado.to_excel(writer, index=False, sheet_name="Lotes")
            st.download_button(
                label="📥 Baixar Excel (.xlsx)",
                data=buffer_excel.getvalue(),
                file_name="lotes_leilao.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        with col_btn3:
            buffer_csv = df_editado.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Baixar CSV",
                data=buffer_csv,
                file_name="lotes_leilao.csv",
                mime="text/csv",
                use_container_width=True
            )

    else:
        st.warning("Nenhum lote foi encontrado no PDF. Verifique se o arquivo possui a relação de lotes.")
else:
    st.info("👆 Por favor, envie o PDF do leilão acima para iniciar a extração.")
