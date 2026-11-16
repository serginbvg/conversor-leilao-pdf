import re
from typing import List, Dict, Any, Optional
import pdfplumber

def parse_descricao(descricao_raw: str, sx_raw: str = "") -> Dict[str, Any]:
    """
    Decompõe o texto de descrição do lote.
    Exemplos:
    - 'BEZERRA(S) NELORE DE 12 MS' -> categoria: 'BEZERRA', raca: 'NELORE', meses: 12
    - 'GARROTE(S) CRUZ. INDUSTRIAL DE 16 MS' -> categoria: 'GARROTE', raca: 'CRUZ. INDUSTRIAL', meses: 16
    - 'VACA(S) PARIDA(S) CRUZADA DE 48 MS' -> categoria: 'VACA PARIDA', raca: 'CRUZADO', meses: 48
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

    # 2. Categoria
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
        sx_upper = sx_raw.upper().strip()
        if sx_upper in ["F", "FEMEA", "FÊMEA"]:
            categoria = "FÊMEA"
        elif sx_upper in ["M", "MACHO"]:
            categoria = "MACHO"

    # 3. Raça
    racas_padrao = [
        (r'\bNELORE\b', 'NELORE'),
        (r'\bANELORAD[OA]\(S\)?\b|\bANELORAD[OA]\b', 'ANELORADO'),
        (r'\bCRUZ(?:\.|\s+)?INDUSTRIAL\b', 'CRUZ. INDUSTRIAL'),
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

    sx_limpo = str(sx).strip().upper()
    if sx_limpo.startswith("M"):
        sx_norm = "M"
    elif sx_limpo.startswith("F"):
        sx_norm = "F"
    else:
        sx_norm = sx_limpo

    return {
        "LOTE": str(lote).strip(),
        "QUANTIDADE": int(qtde) if str(qtde).strip().isdigit() else str(qtde).strip(),
        "SEXO": campo_sexo,
        "raca": decomp["raca"],
        "MESES": decomp["meses"],
        "KG": "",
        "LOCAL": str(vendedor).strip(),
        "observacao": str(obs).strip() if obs else "",
        "SX_ORIGINAL": sx_norm,
        "DESCRICAO_ORIGINAL": str(descricao).strip()
    }

def extrair_lotes_de_texto(text: str) -> List[Dict[str, Any]]:
    """
    Extrator multi-formato universal para leilões de gado.
    Suporta:
    - São Germano Leilões (SX = M / F, lotes numéricos ou SN)
    - Boiadeiro Leilões (Sexo = MACHO / FÊMEA, lotes alfanuméricos como 80A, 01, 903)
    - Quebras de linha e caracteres acentuados
    """
    linhas = text.split("\n")
    linhas_completas = []
    buffer_linha = ""

    # Padrão flexível:
    # Lote: 1 a 4 dígitos + letra opcional (ex: 80A, 01) ou SN
    # Quantidade: 1 a 4 dígitos
    # Vendedor: texto livre com acentos
    # Sexo: MACHO, FÊMEA, FEMEA, M, ou F
    # Descrição / resto
    inicio_lote_re = re.compile(
        r'^\s*([0-9]{1,4}[A-Za-z]?|SN)\s+(\d{1,4})\s+(.+?)\s+(MACHO|FÊMEA|FEMEA|[MF])(?:\s+(.*))?$',
        re.IGNORECASE
    )

    palavras_ignorar = [
        "RELAÇÃO DOS LOTES", "RELACAO DOS LOTES", "LOTE QTDE", "TOTAL MACHO",
        "COMISSÃO", "COMISSAO", "PAG.:", "LEILAO DE GADO DE CORTE",
        "TATERSAL", "TATHERSAL", "CONDICAO DE PAGTO", "CONDIÇÃO DE PAGTO"
    ]

    for l in linhas:
        l_strip = l.strip()
        if not l_strip:
            continue
        # Ignora cabeçalhos ou rodapés típicos
        if any(ign in l_strip.upper() for ign in palavras_ignorar):
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
            sx = m.group(4).strip()
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
    Lê qualquer PDF de leilão via pdfplumber e extrai os lotes automaticamente.
    """
    lotes_extraidos = []

    with pdfplumber.open(pdf_path_or_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text(layout=False)
            if text:
                lotes_pagina = extrair_lotes_de_texto(text)
                lotes_extraidos.extend(lotes_pagina)

    return lotes_extraidos
