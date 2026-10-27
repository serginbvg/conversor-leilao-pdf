import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict, Any, Optional
import json

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

COLUNAS_PADRAO = ["LOTE", "QUANTIDADE", "SEXO", "raca", "MESES", "KG", "LOCAL", "observacao"]

def obter_cliente_gspread(credenciais_info: Any):
    """
    Autentica com o Google Sheets usando credenciais de Service Account.
    Pode receber:
    - Caminho para arquivo .json
    - Dicionário com as credenciais
    - String JSON com o conteúdo das credenciais
    """
    if isinstance(credenciais_info, str):
        if credenciais_info.strip().startswith("{"):
            info = json.loads(credenciais_info)
            creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        else:
            creds = Credentials.from_service_account_file(credenciais_info, scopes=SCOPES)
    elif isinstance(credenciais_info, dict):
        creds = Credentials.from_service_account_info(credenciais_info, scopes=SCOPES)
    else:
        raise ValueError("Formato de credenciais inválido. Forneça o arquivo JSON ou as credenciais.")

    return gspread.authorize(creds)

def sobrepor_lotes_na_planilha(
    client: gspread.Client,
    spreadsheet_id: str,
    lotes: List[Dict[str, Any]],
    gid: Optional[int] = None
) -> Dict[str, Any]:
    """
    Limpa a planilha existente e sobrepõe com os novos dados de lotes do leilão.
    Mantém as colunas: ['LOTE', 'QUANTIDADE', 'SEXO', 'raca', 'MESES', 'KG', 'LOCAL', 'observacao']
    """
    sh = client.open_by_key(spreadsheet_id)

    # Localizar a aba pelo gid ou pegar a primeira aba ativa
    worksheet = None
    if gid is not None:
        for ws in sh.worksheets():
            if ws.id == gid:
                worksheet = ws
                break

    if worksheet is None:
        worksheet = sh.get_worksheet(0)

    # Preparar matriz de dados
    # Linha 1: Cabeçalho
    linhas = [COLUNAS_PADRAO]

    for lote in lotes:
        linha = [
            str(lote.get("LOTE", "")),
            str(lote.get("QUANTIDADE", "")),
            str(lote.get("SEXO", "")),
            str(lote.get("raca", "")),
            str(lote.get("MESES", "")),
            str(lote.get("KG", "")),
            str(lote.get("LOCAL", "")),
            str(lote.get("observacao", ""))
        ]
        linhas.append(linha)

    # Limpar a planilha inteira e reescrever (garante que dados antigos maiores não sobrem)
    worksheet.clear()
    worksheet.update(values=linhas, range_name="A1")

    return {
        "status": "sucesso",
        "aba": worksheet.title,
        "total_linhas": len(lotes)
    }
