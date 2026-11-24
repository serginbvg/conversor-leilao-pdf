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

def extrair_lotes_de_tabela_page(page, col_map_anterior: Optional[Dict[str, int]] = None):
    """
    Extrai os lotes a partir da estrutura nativa de tabela com bordas do pdfplumber.
    Suporta cabeçalho em caixa separada da grade de dados (ex: São Germano Leilões)
    e células mescladas de rodapé (removendo subcolunas None).
    Retorna (lotes_da_pagina, col_map_atualizado).
    """
    lotes = []
    col_map = col_map_anterior
    try:
        tables = page.extract_tables()
        if not tables:
            return [], col_map

        for table in tables:
            if not table:
                continue

            for row in table:
                if not row or not any(row):
                    continue

                # Remove None (subcélulas de mesclagem geradas pelo pdfplumber) e limpa espaços/quebras
                clean_row = [re.sub(r"\s+", " ", str(c)).strip() for c in row if c is not None]
                if not clean_row or not any(clean_row):
                    continue

                row_upper = " ".join(clean_row).upper()

                # Detecta linha de cabeçalho (mesmo que venha isolada em uma tabela de 1 linha)
                if "LOTE" in row_upper and any(q in row_upper for q in ["QTDE", "QUANTIDADE", "QTE", "QUANT", "CAB"]):
                    cmap = {"lote": -1, "qtde": -1, "vend": -1, "sx": -1, "desc": -1, "obs": -1}
                    for idx, c_str in enumerate(clean_row):
                        cu = c_str.upper()
                        if "LOTE" in cu:
                            cmap["lote"] = idx
                        elif any(q in cu for q in ["QTDE", "QUANTIDADE", "QTE", "QUANT", "CAB"]):
                            cmap["qtde"] = idx
                        elif any(v in cu for v in ["VENDEDOR", "FAZENDA", "LOCAL", "PROPRIEDADE", "ORIGEM"]):
                            cmap["vend"] = idx
                        elif "SEXO" in cu or cu == "SX":
                            cmap["sx"] = idx
                        elif "DESC" in cu or "CATEGORIA" in cu or "ANIMAL" in cu:
                            cmap["desc"] = idx
                        elif "OBS" in cu:
                            cmap["obs"] = idx
                    if cmap["lote"] != -1 and cmap["qtde"] != -1:
                        col_map = cmap
                    continue

                # Ignora linhas de totalizadores ou rodapés
                if any(fim in row_upper for fim in [
                    "TOTAL MACHO", "TOTAL FÊMEA", "TOTAL FEMEA", "TOTAL GERAL",
                    "COMISSÃO", "COMISSAO", "CONDIÇÃO DE PAGTO", "CONDICAO DE PAGTO",
                    "PAG.:", "RELAÇÃO DOS LOTES", "RELACAO DOS LOTES"
                ]):
                    continue

                if col_map is not None:
                    def get_col(key: str) -> str:
                        pos = col_map.get(key, -1)
                        return clean_row[pos] if pos != -1 and pos < len(clean_row) else ""

                    lote_val = get_col("lote")
                    qtde_val = get_col("qtde")

                    # Se lote válido (numérico ou alfanumérico como 80A, 01, 018, SN) e quantidade numérica
                    if re.match(r"^(?:[0-9]{1,4}[A-Za-z]?|SN)$", lote_val, re.IGNORECASE) and qtde_val.isdigit():
                        lote_formatado = formatar_lote_para_planilha(
                            lote_val,
                            qtde_val,
                            get_col("vend"),
                            get_col("sx"),
                            get_col("desc"),
                            get_col("obs"),
                        )
                        lotes.append(lote_formatado)
    except Exception:
        return [], col_map

    return lotes, col_map

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
    col_map = None
    with pdfplumber.open(pdf_path_or_file) as pdf:
        for page in pdf.pages:
            lotes_tabela, col_map = extrair_lotes_de_tabela_page(page, col_map)
            if lotes_tabela and len(lotes_tabela) > 0:
                lotes_extraidos.extend(lotes_tabela)
            else:
                text = page.extract_text(layout=False)
                if text:
                    lotes_pagina = extrair_lotes_de_texto(text)
                    lotes_extraidos.extend(lotes_pagina)

    return lotes_extraidos
