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
st.markdown('<div class="sub-title">Extraia automaticamente os lotes de múltiplos formatos de PDF e sincronize os campos desejados com sua planilha do Google Drive</div>', unsafe_allow_html=True)

URL_WEBHOOK_PADRAO = "https://script.google.com/macros/s/AKfycbxhV6UyshMf9pOmQvT3daJUFMpPpWSfFlGIDWT-v04zS7QKddtvxizQCjkB0-zEThwcaw/exec"
ID_PLANILHA_PADRAO = "16I1RSk_WBZAk9bvU4kbKjrv9slWMqL1lFbbSFaEl5PU"

# Barra lateral com métodos de integração
with st.sidebar:
    st.header("⚙️ Conexão com a Planilha")
    
    metodo = st.radio(
        "Como deseja conectar?",
        ["🔗 Webhook do Apps Script (Mais Fácil)", "🔑 Conta de Serviço (Google Cloud)"],
        index=0
    )

    webhook_url = URL_WEBHOOK_PADRAO
    creds_source = None
    spreadsheet_id = ID_PLANILHA_PADRAO
    gid_input = "0"

    if metodo == "🔗 Webhook do Apps Script (Mais Fácil)":
        st.markdown("**URL do Webhook conectada:**")
        webhook_input = st.text_input(
            "URL do Webhook (Google Apps Script)",
            value=URL_WEBHOOK_PADRAO,
            help="Cole a URL do App da Web gerada no menu Extensões > Apps Script da sua planilha"
        )
        if webhook_input:
            webhook_url = webhook_input
        with st.expander("❓ Como gerar essa URL em 1 minuto?"):
            st.markdown("""
            1. Abra sua planilha do Google.
            2. Vá em **Extensões** ➔ **Apps Script**.
            3. Cole o código do Webhook.
            4. Clique em **Implantar** ➔ **Nova implantação** ➔ Tipo: **App da Web**.
            5. Defina: Quem tem acesso = *Qualquer pessoa*.
            6. Copie a URL gerada e cole aqui!
            """)

    else:
        spreadsheet_id = st.text_input(
            "ID da Planilha Google",
            value=ID_PLANILHA_PADRAO
        )
        gid_input = st.text_input(
            "GID da Aba (opcional)",
            value="0"
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
    help="Envie o arquivo PDF com a relação dos lotes (São Germano, Boiadeiro, etc.)"
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

        st.markdown("---")
        st.markdown("### 🎯 Seleção de Campos para Envio")
        st.caption("Escolha quais colunas você quer enviar para a sua planilha do Google. Desmarque as colunas que não desejar incluir:")

        colunas_selecionadas = st.multiselect(
            "Campos selecionados:",
            options=COLUNAS_PADRAO,
            default=COLUNAS_PADRAO,
            help="Arraste ou desmarque para personalizar a ordem ou remover colunas."
        )

        if not colunas_selecionadas:
            st.warning("⚠️ Selecione pelo menos 1 coluna para visualizar e gravar na planilha.")
        else:
            st.markdown("### 📋 Conferência dos Lotes a Enviar")
            st.caption("Você pode alterar qualquer informação diretamente na tabela antes de enviar:")

            df_exibicao = df_lotes[colunas_selecionadas]

            df_editado = st.data_editor(
                df_exibicao,
                use_container_width=True,
                num_rows="dynamic",
                key="editor_lotes"
            )

            st.markdown("---")

            col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])

            with col_btn1:
                label_gravar = f"🚀 Gravar {len(df_editado)} Lotes na Planilha Google"
                if st.button(label_gravar, type="primary", use_container_width=True):
                    dados_finais = df_editado.to_dict(orient="records")
                    
                    # Opção 1: Webhook
                    if metodo.startswith("🔗"):
                        if not webhook_url:
                            st.error("⚠️ Cole a URL do Webhook na barra lateral à esquerda.")
                        else:
                            with st.spinner("Enviando dados diretamente para a planilha via Webhook..."):
                                try:
                                    res = gravar_via_webhook(webhook_url, dados_finais, colunas=colunas_selecionadas)
                                    st.success(f"🎉 Sucesso! {len(dados_finais)} lotes foram sobrepostos na sua planilha com as colunas: {', '.join(colunas_selecionadas)}!")
                                    st.markdown(f"👉 [**Clique aqui para abrir sua Planilha Atualizada**](https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit)")
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
                                    resultado = sobrepor_lotes_na_planilha(cliente, spreadsheet_id.strip(), dados_finais, gid=gid_val, colunas=colunas_selecionadas)
                                    st.success(f"🎉 Sucesso! {resultado['total_linhas']} lotes foram sobrepostos com as colunas: {', '.join(colunas_selecionadas)}!")
                                    link_planilha = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id.strip()}/edit"
                                    if gid_val:
                                        link_planilha += f"#gid={gid_val}"
                                    st.markdown(f"👉 [**Clique aqui para abrir sua Planilha Atualizada**](https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit)")
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
