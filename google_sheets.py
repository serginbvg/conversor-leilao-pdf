import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict, Any, Optional
import json
import requests

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

COLUNAS_PADRAO = ["LOTE", "QUANTIDADE", "SEXO", "raca", "MESES", "KG", "LOCAL", "observacao"]

def preparar_linhas_matriz(lotes: List[Dict[str, Any]]) -> List[List[str]]:
    """
    Monta a matriz com o cabeçalho e todas as linhas formatadas.
    """
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
    return linhas

def gravar_via_webhook(webhook_url: str, lotes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Grava os lotes na planilha enviando diretamente para o Webhook do Google Apps Script.
    Não exige nenhuma conta de serviço ou arquivo JSON.
    """
    linhas = preparar_linhas_matriz(lotes)
    payload = {"linhas": linhas}

    headers = {"Content-Type": "application/json"}
    response = requests.post(webhook_url.strip(), json=payload, headers=headers, timeout=45)

    if response.status_code == 200 or response.status_code == 302:
        try:
            return response.json()
        except:
            return {"status": "sucesso", "total": len(lotes)}
    else:
        raise Exception(f"Erro no webhook (status {response.status_code}): {response.text}")

def obter_cliente_gspread(credenciais_info: Any):
    """
    Autentica com o Google Sheets usando credenciais de Service Account.
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
        raise ValueError("Formato de credenciais inválido.")

    return gspread.authorize(creds)

def sobrepor_lotes_na_planilha(
    client: gspread.Client,
    spreadsheet_id: str,
    lotes: List[Dict[str, Any]],
    gid: Optional[int] = None
) -> Dict[str, Any]:
    """
    Limpa a planilha existente e sobrepõe com os novos dados de lotes do leilão via gspread.
    """
    sh = client.open_by_key(spreadsheet_id)

    worksheet = None
    if gid is not None:
        for ws in sh.worksheets():
            if ws.id == gid:
                worksheet = ws
                break

    if worksheet is None:
        worksheet = sh.get_worksheet(0)

    linhas = preparar_linhas_matriz(lotes)

    worksheet.clear()
    worksheet.update(values=linhas, range_name="A1")

    return {
        "status": "sucesso",
        "aba": worksheet.title,
        "total_linhas": len(lotes)
    }
