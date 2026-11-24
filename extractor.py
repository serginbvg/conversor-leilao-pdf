import re
from typing import List, Dict, Any, Optional
import pdfplumber

PLURAIS_CATEGORIAS = {
    "BEZERRO": "BEZERROS",
    "BEZERRA": "BEZERRAS",
    "NOVILHA": "NOVILHAS",
    "GARROTE": "GARROTES",
    "BOI": "BOIS",
    "VACA": "VACAS",
    "TOURO": "TOUROS",
    "VACA PARIDA": "VACAS PARIDAS",
}

SINGULARES_CATEGORIAS = {v: k for k, v in PLURAIS_CATEGORIAS.items()}

def pluralizar_categoria(cat: str, qtde: int) -> str:
    if not cat:
        return ""
    cat_limpa = cat.upper().replace("(S)", "").strip()
    if qtde > 1:
        return PLURAIS_CATEGORIAS.get(cat_limpa, cat_limpa if cat_limpa.endswith("S") else cat_limpa + "S")
    else:
        return SINGULARES_CATEGORIAS.get(cat_limpa, cat_limpa)

def pluralizar_sexo(sexo: str, qtde: int) -> str:
    if not sexo:
        return ""
    sexo_limpo = sexo.upper().strip()
    if qtde > 1:
        if sexo_limpo in ["MACHO", "MACHOS"]:
            return "MACHOS"
        elif sexo_limpo in ["FÊMEA", "FEMEA", "FÊMEAS", "FEMEAS"]:
            return "FÊMEAS"
    else:
        if sexo_limpo in ["MACHO", "MACHOS"]:
            return "MACHO"
        elif sexo_limpo in ["FÊMEA", "FEMEA", "FÊMEAS", "FEMEAS"]:
            return "FÊMEA"
    return sexo_limpo

def parse_descricao(descricao_raw: str, sx_raw: str = "") -> Dict[str, Any]:
    """
    Decompõe o texto de descrição do lote em Categoria, Raça e Idade (Meses).
    Suporta variações de meses: 16 MS, 16MS, 16 MESES, 16 MES, 16 MÊS, 16 M, 16M, DE 16.
    """
    if not descricao_raw:
        return {"categoria": "", "raca": "", "meses": ""}

    texto = descricao_raw.replace("\n", " ").strip()

    # 1. Extrair Meses com regex universal ampla
    meses = ""
    regex_meses = re.compile(
        r"(?:(?:DE\s+)?(\d{1,2})\s*(?:M\.?S\.?|MESES|MÊS|MES|M)\b|(?:DE\s+)(\d{1,2})\b)",
        re.IGNORECASE
    )
    meses_match = regex_meses.search(texto)
    if meses_match:
        meses = meses_match.group(1) or meses_match.group(2)
        texto_sem_meses = regex_meses.sub('', texto).strip()
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
        if sx_upper in ["F", "FEMEA", "FÊMEA", "FEMEAS", "FÊMEAS"]:
            categoria = "FÊMEA"
        elif sx_upper in ["M", "MACHO", "MACHOS"]:
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
    sx_limpo = str(sx).strip().upper()
    if sx_limpo in ["M", "MACHO", "MACHOS"]:
        sexo_base = "MACHO"
        sx_norm = "M"
    elif sx_limpo in ["F", "FEMEA", "FÊMEA", "FEMEAS", "FÊMEAS"]:
        sexo_base = "FÊMEA"
        sx_norm = "F"
    else:
        sexo_base = sx_limpo
        sx_norm = sx_limpo

    qtde_num = int(qtde) if str(qtde).strip().isdigit() else 1

    # Concordância gramatical automática de sexo:
    # Se quantidade > 1 -> MACHOS ou FÊMEAS
    # Se quantidade == 1 -> MACHO ou FÊMEA
    sexo_ajustado = pluralizar_sexo(sexo_base, qtde_num)

    decomp = parse_descricao(descricao, sx_limpo)
    categoria_base = decomp["categoria"] if decomp["categoria"] else ("MACHO" if sx_norm == "M" else "FÊMEA" if sx_norm == "F" else "")
    categoria_ajustada = pluralizar_categoria(categoria_base, qtde_num)

    return {
        "LOTE": str(lote).strip(),
        "QUANTIDADE": int(qtde) if str(qtde).strip().isdigit() else str(qtde).strip(),
        "SEXO": sexo_ajustado,
        "SEXO_SINGULAR": sexo_base,
        "CATEGORIA": categoria_ajustada,
        "CATEGORIA_SINGULAR": categoria_base,
        "raca": decomp["raca"],
        "MESES": decomp["meses"],
        "KG": "",
        "LOCAL": str(vendedor).strip(),
        "observacao": str(obs).strip() if obs else "",
        "SX_ORIGINAL": sx_norm,
        "DESCRICAO_ORIGINAL": str(descricao).strip()
    }

def extrair_lotes_de_tabela_page(page) -> List[Dict[str, Any]]:
    """
    Extrai os lotes a partir da estrutura nativa de tabela com bordas do pdfplumber.
    Isola 100% as colunas sem risco de misturar texto entre células.
    """
    lotes = []
    try:
        tables = page.extract_tables()
        if not tables:
            return []

        for table in tables:
            if not table or len(table) < 2:
                continue

            header_idx = -1
            col_lote = -1
            col_qtde = -1
            col_vend = -1
            col_sx = -1
            col_desc = -1
            col_obs = -1

            for r_idx, row in enumerate(table):
                if not row:
                    continue
                row_str = " ".join([str(c).upper() for c in row if c])
                if "LOTE" in row_str and any(q in row_str for q in ["QTDE", "QUANTIDADE", "QTE", "QUANT"]):
                    header_idx = r_idx
                    for idx, c in enumerate(row):
                        c_str = str(c).upper().strip() if c else ""
                        if "LOTE" in c_str:
                            col_lote = idx
                        elif any(q in c_str for q in ["QTDE", "QUANTIDADE", "QTE", "QUANT"]):
                            col_qtde = idx
                        elif any(v in c_str for v in ["VENDEDOR", "FAZENDA", "LOCAL", "PROPRIEDADE"]):
                            col_vend = idx
                        elif "SEXO" in c_str or "SX" in c_str:
                            col_sx = idx
                        elif "DESC" in c_str:
                            col_desc = idx
                        elif "OBS" in c_str:
                            col_obs = idx
                    break

            if header_idx != -1 and col_lote != -1 and col_qtde != -1:
                for row in table[header_idx + 1:]:
                    if not row or not any(row):
                        continue

                    # Ignora linhas de totalizadores (ex: 54 1684 Total Macho: 1684...) ou rodapés
                    row_full_str = " ".join([str(c).upper() for c in row if c])
                    if any(fim in row_full_str for fim in [
                        "TOTAL MACHO", "TOTAL FÊMEA", "TOTAL FEMEA", "TOTAL GERAL",
                        "COMISSÃO", "COMISSAO", "CONDIÇÃO DE PAGTO", "CONDICAO DE PAGTO"
                    ]):
                        continue

                    lote_val = str(row[col_lote]).replace("\n", " ").strip() if col_lote < len(row) and row[col_lote] else ""
                    if not lote_val or any(fim in lote_val.upper() for fim in ["TOTAL", "COMISS", "CONDIC", "PAG."]):
                        continue

                    qtde_val = str(row[col_qtde]).replace("\n", " ").strip() if col_qtde < len(row) and row[col_qtde] else ""
                    vend_val = str(row[col_vend]).replace("\n", " ").strip() if col_vend != -1 and col_vend < len(row) and row[col_vend] else ""
                    sx_val = str(row[col_sx]).replace("\n", " ").strip() if col_sx != -1 and col_sx < len(row) and row[col_sx] else ""
                    desc_val = str(row[col_desc]).replace("\n", " ").strip() if col_desc != -1 and col_desc < len(row) and row[col_desc] else ""
                    obs_val = str(row[col_obs]).replace("\n", " ").strip() if col_obs != -1 and col_obs < len(row) and row[col_obs] else ""

                    # Se lote válido (numérico ou alfanumérico como 80A, 01, SN)
                    if re.match(r'^(?:[0-9]{1,4}[A-Za-z]?|SN)$', lote_val, re.IGNORECASE):
                        lote_formatado = formatar_lote_para_planilha(lote_val, qtde_val, vend_val, sx_val, desc_val, obs_val)
                        lotes.append(lote_formatado)
    except Exception:
        return []

    return lotes

def extrair_lotes_de_texto(text: str) -> List[Dict[str, Any]]:
    """
    Extrator multi-formato universal para leilões de gado via texto.
    Suporta quebras de linha no nome do vendedor (ex: Lote 32 'FAZ NOSSA SENHORA DE \n APARECIDA').
    """
    linhas = text.split("\n")
    linhas_completas = []
    buffer_linha = ""

    # Identifica o início garantido de um lote: [Lote] [Quantidade] [Texto...]
    inicio_novo_lote_re = re.compile(
        r'^\s*([0-9]{1,4}[A-Za-z]?|SN)\s+(\d{1,4})\s+(.+)$',
        re.IGNORECASE
    )

    # Identifica a estrutura completa após juntar linhas quebradas
    lote_completo_re = re.compile(
        r'^\s*([0-9]{1,4}[A-Za-z]?|SN)\s+(\d{1,4})\s+(.+?)\s+(MACHO|FÊMEA|FEMEA|[MF])(?:\s+(.*))?$',
        re.IGNORECASE
    )

    palavras_ignorar = [
        "RELAÇÃO DOS LOTES", "RELACAO DOS LOTES", "LOTE QTDE", "PAG.:", "LEILAO DE GADO DE CORTE",
        "TATERSAL", "TATHERSAL", "CONDICAO DE PAGTO", "CONDIÇÃO DE PAGTO"
    ]

    for l in linhas:
        l_strip = l.strip()
        if not l_strip:
            continue

        # Se encontrou o totalizador da página ou rodapé final, encerra a leitura desta página
        if any(fim in l_strip.upper() for fim in ["TOTAL MACHO", "TOTAL FÊMEA", "TOTAL FEMEA", "TOTAL GERAL", "COMISSÃO", "COMISSAO"]):
            if buffer_linha:
                linhas_completas.append(buffer_linha)
                buffer_linha = ""
            break

        if any(ign in l_strip.upper() for ign in palavras_ignorar):
            continue

        # Se a linha começa com um novo lote (Número/SN + Quantidade)
        if inicio_novo_lote_re.match(l_strip):
            if buffer_linha:
                linhas_completas.append(buffer_linha)
            buffer_linha = l_strip
        else:
            if buffer_linha:
                if not any(ign in l_strip.upper() for ign in ["@", "ROD GO", "RODOVIA", "CIADADE:", "CIDADE:", "UF:", "DATA:"]):
                    buffer_linha += " " + l_strip

    if buffer_linha:
        linhas_completas.append(buffer_linha)

    lotes = []
    for linha in linhas_completas:
        m = lote_completo_re.match(linha)
        if m:
            lote = m.group(1).strip()
            qtde = m.group(2).strip()
            vendedor = m.group(3).strip()
            sx = m.group(4).strip()
            resto = m.group(5).strip() if m.group(5) else ""

            obs = ""
            desc = resto

            # Busca onde termina a especificação de idade/meses
            match_ms = re.search(
                r'^(.*?\b\d{1,2}\s*(?:M\.?S\.?|MESES|MÊS|MES|M)\b)(.*)$',
                resto,
                re.IGNORECASE
            )
            if match_ms:
                desc = match_ms.group(1).strip()
                obs = match_ms.group(2).strip()
            else:
                match_de = re.search(r'^(.*?\bDE\s+\d{1,2}\b)(.*)$', resto, re.IGNORECASE)
                if match_de:
                    desc = match_de.group(1).strip()
                    obs = match_de.group(2).strip()

            lotes.append(formatar_lote_para_planilha(lote, qtde, vendedor, sx, desc, obs))

    return lotes

def extrair_lotes_de_pdf(pdf_path_or_file) -> List[Dict[str, Any]]:
    """
    Lê qualquer PDF de leilão com estratégia híbrida:
    1. Tenta extração de tabela estruturada nativa com bordas (máxima precisão).
    2. Se não identificar tabela ou colunas, usa o parser de texto universal.
    """
    lotes_extraidos = []
    with pdfplumber.open(pdf_path_or_file) as pdf:
        for page in pdf.pages:
            lotes_tabela = extrair_lotes_de_tabela_page(page)
            if lotes_tabela and len(lotes_tabela) > 0:
                lotes_extraidos.extend(lotes_tabela)
            else:
                text = page.extract_text(layout=False)
                if text:
                    lotes_pagina = extrair_lotes_de_texto(text)
                    lotes_extraidos.extend(lotes_pagina)

    return lotes_extraidos
