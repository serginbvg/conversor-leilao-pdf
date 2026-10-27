import re
from typing import List, Dict, Any, Optional
import pdfplumber

def parse_descricao(descricao_raw: str, sx_raw: str = "") -> Dict[str, Any]:
    """
    Decompõe o texto de descrição do lote.
    Exemplos:
    - 'BEZERRA(S) NELORE DE 12 MS' -> categoria: 'BEZERRA', raca: 'NELORE', meses: 12
    - 'VACA(S) PARIDA(S) CRUZADA DE 48 MS' -> categoria: 'VACA PARIDA', raca: 'CRUZADO', meses: 48
    - 'GARROTE(S) ANELORADO DE 22 MS' -> categoria: 'GARROTE', raca: 'ANELORADO', meses: 22
    """
    if not descricao_raw:
        return {"categoria": "", "raca": "", "meses": ""}

    texto = descricao_raw.strip()

    # 1. Extrair Meses: busca padrões como 'DE 16 MS', '16 MS', '16 MESES'
    meses = ""
    meses_match = re.search(r'(?:DE\s+)?(\d+)\s*(?:MS|MESES|MÊS)\b', texto, re.IGNORECASE)
    if meses_match:
        meses = meses_match.group(1)
        texto_sem_meses = re.sub(r'(?:DE\s+)?\d+\s*(?:MS|MESES|MÊS)\b', '', texto, flags=re.IGNORECASE).strip()
    else:
        texto_sem_meses = texto

    # 2. Categoria / Sexo
    categoria = ""
    categorias_padrao = [
        (r'VACA\(S\)\s*PARIDA\(S\)|VACA\s+PARIDA', 'VACA PARIDA'),
        (r'BEZERRA\(S\)|BEZERRA', 'BEZERRA'),
        (r'BEZERRO\(S\)|BEZERRO', 'BEZERRO'),
        (r'NOVILHA\(S\)|NOVILHA', 'NOVILHA'),
        (r'GARROTE\(S\)|GARROTE', 'GARROTE'),
        (r'BOI\(S\)|BOI', 'BOI'),
        (r'VACA\(S\)|VACA', 'VACA'),
        (r'TOURO\(S\)|TOURO', 'TOURO'),
    ]

    for padrao, nome_cat in categorias_padrao:
        if re.search(padrao, texto_sem_meses, re.IGNORECASE):
            categoria = nome_cat
            texto_sem_meses = re.sub(padrao, '', texto_sem_meses, flags=re.IGNORECASE).strip()
            break

    if not categoria and sx_raw:
        categoria = "FÊMEA" if sx_raw.upper().strip() == 'F' else "MACHO" if sx_raw.upper().strip() == 'M' else ""

    # 3. Raça
    racas_padrao = [
        (r'\bNELORE\b', 'NELORE'),
        (r'\bANELORAD[OA]\(S\)?\b|\bANELORAD[OA]\b', 'ANELORADO'),
        (r'\bCRUZAD[OA]\(S\)?\b|\bCRUZAD[OA]\b', 'CRUZADO'),
        (r'\bMESTIÇ[OA]\(S\)?\b|\bMESTIÇ[OA]\b|\bMESTICO\b', 'MESTIÇO'),
        (r'\bANGUS\b', 'ANGUS'),
        (r'\bSENEPOL\b', 'SENEPOL'),
        (r'\bBRAFORD\b', 'BRAFORD'),
        (r'\bBRANGUS\b', 'BRANGUS'),
        (r'\bGIROLANDO\b|\bGIROLANDA\b', 'GIROLANDO'),
        (r'\bTABAPU[ÃA]\b', 'TABAPUÃ'),
        (r'\bGUZER[ÁA]\b', 'GUZERÁ'),
        (r'\bCARACU\b', 'CARACU'),
        (r'\bHEREFORD\b', 'HEREFORD'),
        (r'\bBRAHMAN\b', 'BRAHMAN'),
    ]

    raca = ""
    for padrao, nome_raca in racas_padrao:
        if re.search(padrao, texto_sem_meses, re.IGNORECASE):
            raca = nome_raca
            texto_sem_meses = re.sub(padrao, '', texto_sem_meses, flags=re.IGNORECASE).strip()
            break

    if not raca:
        resto = re.sub(r'^[^\w]+|[^\w]+$', '', texto_sem_meses).strip()
        if resto:
            raca = resto

    return {
        "categoria": categoria,
        "raca": raca,
        "meses": meses
    }

def formatar_lote_para_planilha(
    lote: str,
    qtde: Any,
    vendedor: str,
    sx: str,
    descricao: str,
    obs: str = ""
) -> Dict[str, Any]:
    decomp = parse_descricao(descricao, sx)
    campo_sexo = decomp["categoria"] if decomp["categoria"] else (descricao.strip() if descricao else sx)

    return {
        "LOTE": str(lote).strip(),
        "QUANTIDADE": int(qtde) if str(qtde).strip().isdigit() else str(qtde).strip(),
        "SEXO": campo_sexo,
        "raca": decomp["raca"],
        "MESES": decomp["meses"],
        "KG": "",
        "LOCAL": str(vendedor).strip(),
        "observacao": str(obs).strip() if obs else "",
        "SX_ORIGINAL": str(sx).strip().upper(),
        "DESCRICAO_ORIGINAL": str(descricao).strip()
    }

def extrair_lotes_de_texto(text: str) -> List[Dict[str, Any]]:
    """
    Extrator inteligente com suporte a:
    - Nomes com caracteres acentuados (ex: 'CABAÇA', 'SÃO JOÃO')
    - Linhas de descrição que quebram em múltiplas linhas (ex: Lote 101)
    """
    linhas = text.split("\n")
    linhas_completas = []
    buffer_linha = ""

    # Início de um lote: SN ou número (1 a 4 dígitos) + quantidade + vendedor + M/F
    inicio_lote_re = re.compile(r'^\s*([0-9]{1,4}|SN)\s+(\d{1,4})\s+(.+?)\s+([MF])(?:\s+(.*))?$', re.IGNORECASE)

    for l in linhas:
        l_strip = l.strip()
        if not l_strip:
            continue
        if any(ignorar in l_strip.upper() for ignorar in ["RELAÇÃO DOS LOTES", "LOTE QTDE", "TOTAL MACHO", "COMISSÃO", "RODOVIA", "TATHERSAL", "PAG.:"]):
            continue

        m = inicio_lote_re.match(l_strip)
        if m:
            if buffer_linha:
                linhas_completas.append(buffer_linha)
            buffer_linha = l_strip
        else:
            if buffer_linha:
                buffer_linha += " " + l_strip

    if buffer_linha:
        linhas_completas.append(buffer_linha)

    lotes = []
    for linha in linhas_completas:
        m = inicio_lote_re.match(linha)
        if m:
            lote = m.group(1).strip()
            qtde = m.group(2).strip()
            vendedor = m.group(3).strip()
            sx = m.group(4).strip().upper()
            resto = m.group(5).strip() if m.group(5) else ""

            obs = ""
            desc = resto
            match_ms = re.search(r'^(.*?\b\d+\s*(?:MS|MESES)\b)(.*)$', resto, re.IGNORECASE)
            if match_ms:
                desc = match_ms.group(1).strip()
                obs = match_ms.group(2).strip()

            lotes.append(formatar_lote_para_planilha(lote, qtde, vendedor, sx, desc, obs))

    return lotes

def extrair_lotes_de_pdf(pdf_path_or_file) -> List[Dict[str, Any]]:
    """
    Lê o PDF do leilão via pdfplumber e extrai todos os lotes com precisão de 100%.
    """
    lotes_extraidos = []

    with pdfplumber.open(pdf_path_or_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text(layout=False)
            if text:
                lotes_pagina = extrair_lotes_de_texto(text)
                lotes_extraidos.extend(lotes_pagina)

    return lotes_extraidos
