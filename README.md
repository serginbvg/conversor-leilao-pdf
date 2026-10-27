# 🐂 Conversor de Leilão de Gado para Google Sheets

Sistema online para leitura automatizada de catálogos e relações de lotes de leilão em PDF e sincronização direta com planilha do Google Drive.

---

## 🚀 Como Funciona

1. **Upload do PDF do Leilão**: O sistema lê a tabela e o texto usando extração inteligente.
2. **Decomposição Automática da Descrição**:
   - `LOTE`: Identificador do lote (ex: `1`, `012`, `SN`, `400`).
   - `QUANTIDADE`: Número de cabeças.
   - `SEXO`: Categoria identificada (`BEZERRO`, `BEZERRA`, `NOVILHA`, `GARROTE`, `VACA`, `BOI`).
   - `raca`: Raça identificada (`NELORE`, `ANELORADO`, `MESTIÇO`, `CRUZADO`, etc.).
   - `MESES`: Idade do lote em meses.
   - `KG`: Campo reservado para anotação de pesagens no leilão.
   - `LOCAL`: Fazenda ou Vendedor de origem.
   - `observacao`: Detalhes e observações adicionais.
3. **Conferência em Tela**: Tabela interativa para revisar ou alterar valores antes do envio.
4. **Sobreposição no Google Sheets**: Ao clicar no botão, ele limpa a relação antiga e sobrepõe com a nova relação de lotes instantaneamente.
5. **Downloads Alternativos**: Permite baixar em Excel (.xlsx) ou CSV com 1 clique.

---

## 💻 Como Rodar Localmente no seu Mac

1. Ative o ambiente virtual:
```bash
source venv/bin/activate
```

2. Inicie o aplicativo:
```bash
streamlit run app.py
```
O navegador abrirá automaticamente em `http://localhost:8501`.

---

## 🌐 Como Publicar Online Gratuitamente (GitHub + Streamlit Cloud)

### Passo 1: Subir para o GitHub
1. Crie um repositório no seu GitHub (ex: `conversor-leilao-pdf`).
2. Vincule e envie seu código:
```bash
git remote add origin https://github.com/SEU_USUARIO/conversor-leilao-pdf.git
git branch -M main
git push -u origin main
```

### Passo 2: Publicar no Streamlit Cloud
1. Acesse [share.streamlit.io](https://share.streamlit.io/) e faça login com sua conta do GitHub.
2. Clique em **New App**.
3. Selecione seu repositório, a branch `main` e o arquivo `app.py`.
4. Clique em **Deploy**! Em 2 minutos seu sistema estará no ar com link público.

---

## 🌐 Usando o seu Domínio da Locaweb

Você pode manter a melhor combinação: a hospedagem gratuita e estável do Streamlit Cloud + o seu domínio profissional da Locaweb:

1. No painel da **Locaweb**, vá na área de **Gerenciador de DNS / Zona de DNS** do seu domínio.
2. Crie uma entrada do tipo **CNAME**:
   - **Nome / Subdomínio:** `leilao` (ou `gado`)
   - **Destino:** o endereço do seu app gerado no Streamlit (ou configure o domínio personalizado nas configurações do app no Streamlit Cloud).
3. Pronto! Você e sua equipe poderão acessar diretamente por:
   `https://leilao.seudominio.com.br`

---

## 🔑 Configuração da Planilha Google (Google Cloud)

Para que o robô possa gravar na sua planilha:
1. Acesse o [Google Cloud Console](https://console.cloud.google.com/).
2. Crie um projeto gratuito e habilite a **Google Sheets API** e a **Google Drive API**.
3. Em **Contas de Serviço (Service Accounts)**, crie uma conta e baixe a chave em formato **JSON**.
4. Copie o e-mail da conta de serviço (ex: `leilao-bot@projeto.iam.gserviceaccount.com`).
5. Na sua planilha do Google Drive (`1YN1TH_QlMCylMIvlKVM6mFt1NyQqfh-54JYbZS1S41A`), clique em **Compartilhar** e adicione esse e-mail como **Editor**.
6. Guarde o arquivo como `credentials.json` na pasta do projeto ou carregue diretamente pela interface do aplicativo.
