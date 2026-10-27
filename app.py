import streamlit as st
import pandas as pd
import io
import os
import json
from extractor import extrair_lotes_de_pdf, formatar_lote_para_planilha, parse_descricao
from google_sheets import obter_cliente_gspread, sobrepor_lotes_na_planilha, COLUNAS_PADRAO

st.set_page_config(
    page_title="Conversor de Leilão para Google Sheets",
    page_icon="🐂",
    layout="wide"
)

# Estilização personalizada
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
    .metric-card {
        background-color: #f1f8e9;
        border-radius: 8px;
        padding: 12px;
        border-left: 5px solid #4caf50;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🐂 Conversor de Leilão de Gado</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Extraia automaticamente os lotes do PDF do leilão e lance direto na sua planilha do Google Drive</div>', unsafe_allow_html=True)

# Barra lateral com configurações
with st.sidebar:
    st.header("⚙️ Configurações da Planilha")
    spreadsheet_id = st.text_input(
        "ID da Planilha Google",
        value="1YN1TH_QlMCylMIvlKVM6mFt1NyQqfh-54JYbZS1S41A",
        help="Encontrado na URL da sua planilha"
    )
    gid_input = st.text_input(
        "GID da Aba (opcional)",
        value="673667983",
        help="O identificador da aba (#gid=...)"
    )

    st.markdown("---")
    st.subheader("🔑 Conexão com Google Drive")
    
    creds_source = None
    # 1. Verifica se está nos segredos do Streamlit
    if "gcp_service_account" in st.secrets:
        creds_source = dict(st.secrets["gcp_service_account"])
        st.success("✅ Credenciais ativas via Segredos da Nuvem")
    # 2. Verifica se tem arquivo credentials.json na pasta
    elif os.path.exists("credentials.json"):
        with open("credentials.json", "r", encoding="utf-8") as f:
            creds_source = json.load(f)
        st.success("✅ Arquivo credentials.json detectado localmente")
    else:
        st.info("ℹ️ Para conectar automaticamente, carregue o JSON da Conta de Serviço do Google Cloud abaixo:")
        uploaded_creds = st.file_uploader("Arquivo de Credenciais (.json)", type=["json"], key="creds_file")
        if uploaded_creds:
            try:
                creds_source = json.load(uploaded_creds)
                st.success("✅ Credenciais carregadas!")
            except Exception as e:
                st.error(f"Erro ao ler JSON: {e}")

    with st.expander("❓ Como criar as credenciais do Google?"):
        st.markdown("""
        1. Acesse o [Google Cloud Console](https://console.cloud.google.com/).
        2. Crie um projeto e ative a **Google Sheets API** e a **Google Drive API**.
        3. Vá em **Contas de Serviço** e crie uma chave em formato **JSON**.
        4. Copie o e-mail da conta de serviço (ex: `robô@projeto.iam.gserviceaccount.com`).
        5. Abra sua planilha do Google e clique em **Compartilhar**, adicionando esse e-mail como **Editor**.
        """)

# Upload do PDF principal
uploaded_pdf = st.file_uploader(
    "📄 Selecione ou arraste o PDF do Leilão:",
    type=["pdf"],
    help="Envie o arquivo PDF com a relação dos lotes"
)

if uploaded_pdf is not None:
    with st.spinner("Lendo e interpretando os lotes do PDF..."):
        try:
            # Salvar temporariamente em memória para extrair
            lotes_extraidos = extrair_lotes_de_pdf(uploaded_pdf)
        except Exception as e:
            st.error(f"Erro durante a leitura do PDF: {e}")
            lotes_extraidos = []

    if lotes_extraidos:
        df_lotes = pd.DataFrame(lotes_extraidos)

        # Tratar colunas numéricas para métricas
        df_lotes["QUANTIDADE_NUM"] = pd.to_numeric(df_lotes["QUANTIDADE"], errors="coerce").fillna(0).astype(int)
        total_lotes = len(df_lotes)
        total_cabecas = int(df_lotes["QUANTIDADE_NUM"].sum())
        
        # Identificar Machos e Fêmeas
        total_machos = int(df_lotes[df_lotes["SX_ORIGINAL"] == "M"]["QUANTIDADE_NUM"].sum())
        total_femeas = int(df_lotes[df_lotes["SX_ORIGINAL"] == "F"]["QUANTIDADE_NUM"].sum())

        # Métricas no topo
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📦 Total de Lotes", f"{total_lotes}")
        col2.metric("🐂 Total de Cabeças", f"{total_cabecas}")
        col3.metric("♂️ Machos", f"{total_machos}")
        col4.metric("♀️ Fêmeas", f"{total_femeas}")

        st.markdown("### 📋 Conferência dos Lotes Extraídos")
        st.caption("Você pode conferir os dados ou fazer correções manuais na tabela abaixo antes de enviar para a planilha.")

        colunas_exibicao = ["LOTE", "QUANTIDADE", "SEXO", "raca", "MESES", "KG", "LOCAL", "observacao"]
        df_exibicao = df_lotes[colunas_exibicao]

        # Tabela editável
        df_editado = st.data_editor(
            df_exibicao,
            use_container_width=True,
            num_rows="dynamic",
            key="editor_lotes"
        )

        st.markdown("---")

        # Botões de Ação
        col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])

        with col_btn1:
            if st.button("🚀 Gravar e Sobrepor na Planilha Google", type="primary", use_container_width=True):
                if not creds_source:
                    st.error("⚠️ Para enviar diretamente ao Google Sheets, carregue o arquivo de credenciais na barra lateral.")
                elif not spreadsheet_id:
                    st.error("⚠️ Informe o ID da planilha na barra lateral.")
                else:
                    with st.spinner("Conectando ao Google Sheets e atualizando dados..."):
                        try:
                            cliente = obter_cliente_gspread(creds_source)
                            gid_val = int(gid_input.strip()) if gid_input.strip().isdigit() else None
                            
                            # Converter dataframe editado para lista de dicionários
                            dados_finais = df_editado.to_dict(orient="records")
                            resultado = sobrepor_lotes_na_planilha(cliente, spreadsheet_id.strip(), dados_finais, gid=gid_val)

                            st.success(f"🎉 Sucesso! {resultado['total_linhas']} lotes foram sobrepostos na aba '{resultado['aba']}' da sua planilha!")
                            link_planilha = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id.strip()}/edit"
                            if gid_val:
                                link_planilha += f"#gid={gid_val}"
                            st.markdown(f"👉 [**Clique aqui para abrir sua Planilha Atualizada**]({link_planilha})")
                        except Exception as e:
                            st.error(f"Erro ao gravar na planilha: {e}")
                            st.info("Dica: Verifique se compartilhou a planilha com o e-mail da Conta de Serviço com permissão de 'Editor'.")

        with col_btn2:
            # Exportar Excel
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
            # Exportar CSV
            buffer_csv = df_editado.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Baixar CSV",
                data=buffer_csv,
                file_name="lotes_leilao.csv",
                mime="text/csv",
                use_container_width=True
            )

    else:
        st.warning("Nenhum lote foi encontrado no PDF. Verifique se o formato do documento possui a tabela de lotes.")
else:
    st.info("👆 Por favor, envie o PDF do leilão acima para iniciar a extração.")
