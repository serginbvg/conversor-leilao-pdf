import re
from typing import List, Dict, Any, Optional
import pdfplumber

def parse_descricao(descricao_raw: str, sx_raw: str = "") -> Dict[str, Any]:
    """
    Decompõe o texto de descrição do lote.
    Exemplos:
    - 'BEZERRA(S) NELORE DE 12 MS' -> categoria: 'BEZERRA', raca: 'NELORE', meses: 12
    - 'VACA(S) PARIDA(S) CRUZADA DE 48 MS' -> categoria: 'VACA PARIDA', raca: 'CRUZADA', meses: 48
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
        # Remove a parte dos meses do texto para facilitar as outras buscas
        texto_sem_meses = re.sub(r'(?:DE\s+)?\d+\s*(?:MS|MESES|MÊS)\b', '', texto, flags=re.IGNORECASE).strip()
    else:
        texto_sem_meses = texto

    # 2. Categoria / Sexo
    # Categorias comuns de leilão de gado de corte
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

    # Se não identificou categoria específica, podemos usar o sexo ou a primeira palavra
    if not categoria and sx_raw:
        categoria = "FÊMEA" if sx_raw.upper().strip() == 'F' else "MACHO" if sx_raw.upper().strip() == 'M' else ""

    # 3. Raça
    # Procura palavras-chave de raça
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

    # Se ainda sobrar texto relevante sem preencher raça
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
    """
    Estrutura a linha exatamente no padrão das colunas da planilha do Google:
    ['LOTE', 'QUANTIDADE', 'SEXO', 'raca', 'MESES', 'KG', 'LOCAL', 'observacao']
    """
    decomp = parse_descricao(descricao, sx)

    # Formatar o campo SEXO: usamos a categoria extraída (ex: 'BEZERRA', 'GARROTE') ou a descrição
    # O usuário pode optar pela categoria ou descrição.
    campo_sexo = decomp["categoria"] if decomp["categoria"] else (descricao.strip() if descricao else sx)

    return {
        "LOTE": str(lote).strip(),
        "QUANTIDADE": int(qtde) if str(qtde).strip().isdigit() else str(qtde).strip(),
        "SEXO": campo_sexo,
        "raca": decomp["raca"],
        "MESES": decomp["meses"],
        "KG": "",  # Vazio pronto para inserção de pesos
        "LOCAL": str(vendedor).strip(),
        "observacao": str(obs).strip() if obs else "",
        # Campos auxiliares para validação no app
        "SX_ORIGINAL": str(sx).strip().upper(),
        "DESCRICAO_ORIGINAL": str(descricao).strip()
    }

def extrair_lotes_de_pdf(pdf_path_or_file) -> List[Dict[str, Any]]:
    """
    Lê o PDF do leilão via pdfplumber e extrai os lotes formatados.
    Suporta tanto extração por tabela estruturada quanto por análise linha a linha de texto.
    """
    lotes_extraidos = []

    with pdfplumber.open(pdf_path_or_file) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            # 1. Tentar extração via tabelas do pdfplumber
            tables = page.extract_tables()
            tabela_processada = False

            for table in tables:
                if not table or len(table) < 2:
                    continue

                header_idx = -1
                for r_idx, row in enumerate(table):
                    row_str = " ".join([str(c) for c in row if c]).upper()
                    if "LOTE" in row_str and ("QTDE" in row_str or "QUANTIDADE" in row_str):
                        header_idx = r_idx
                        break

                if header_idx != -1:
                    header = [str(c).upper().strip() if c else "" for c in table[header_idx]]
                    # Identificar posições das colunas
                    col_lote = -1
                    col_qtde = -1
                    col_vend = -1
                    col_sx = -1
                    col_desc = -1
                    col_obs = -1

                    for idx, h in enumerate(header):
                        if "LOTE" in h:
                            col_lote = idx
                        elif "QTDE" in h or "QTE" in h or "QUANT" in h:
                            col_qtde = idx
                        elif "VENDEDOR" in h or "FAZENDA" in h or "LOCAL" in h:
                            col_vend = idx
                        elif "SX" in h or "SEXO" in h:
                            col_sx = idx
                        elif "DESC" in h:
                            col_desc = idx
                        elif "OBS" in h:
                            col_obs = idx

                    # Se encontrou as colunas essenciais
                    if col_lote != -1 and col_qtde != -1:
                        for row in table[header_idx + 1:]:
                            if not row or not any(row):
                                continue
                            lote_val = str(row[col_lote]).strip() if col_lote < len(row) and row[col_lote] else ""
                            # Pular rodapé de totais
                            if not lote_val or "TOTAL" in lote_val.upper() or "COMISS" in lote_val.upper():
                                continue

                            qtde_val = row[col_qtde] if col_qtde < len(row) and row[col_qtde] else ""
                            vend_val = row[col_vend] if col_vend != -1 and col_vend < len(row) and row[col_vend] else ""
                            sx_val = row[col_sx] if col_sx != -1 and col_sx < len(row) and row[col_sx] else ""
                            desc_val = row[col_desc] if col_desc != -1 and col_desc < len(row) and row[col_desc] else ""
                            obs_val = row[col_obs] if col_obs != -1 and col_obs < len(row) and row[col_obs] else ""

                            # Limpar quebras de linha internas
                            lote_clean = lote_val.replace("\n", " ").strip()
                            qtde_clean = str(qtde_val).replace("\n", " ").strip()
                            vend_clean = str(vend_val).replace("\n", " ").strip()
                            sx_clean = str(sx_val).replace("\n", " ").strip()
                            desc_clean = str(desc_val).replace("\n", " ").strip()
                            obs_clean = str(obs_val).replace("\n", " ").strip()

                            lote_formatado = formatar_lote_para_planilha(
                                lote_clean, qtde_clean, vend_clean, sx_clean, desc_clean, obs_clean
                            )
                            lotes_extraidos.append(lote_formatado)
                        tabela_processada = True

            # Se a extração por tabela não capturou lotes suficientes, usamos o extrator por texto / linhas
            if not tabela_processada:
                text = page.extract_text()
                if text:
                    linhas_lotes = extrair_lotes_de_texto(text)
                    lotes_extraidos.extend(linhas_lotes)

    return lotes_extraidos

def extrair_lotes_de_texto(text: str) -> List[Dict[str, Any]]:
    """
    Extrator de fallback baseado em expressão regular para ler as linhas de texto do PDF.
    Ex: '1 7 FAZ AGUAS MARINAS F BEZERRA(S) NELORE DE 12 MS FILHAS BOI PO JOAO MAURICIO'
    """
    lotes = []
    linhas = text.split("\n")

    # Padrão:
    # Grupo 1: Lote (números ou SN, ex: 1, 012, 400, SN)
    # Grupo 2: Quantidade (número)
    # Grupo 3: Vendedor
    # Grupo 4: Sexo (M ou F)
    # Grupo 5: Descrição + Obs
    linha_regex = re.compile(
        r'^\s*([0-9]{1,4}|SN)\s+(\d+)\s+([A-Z0-9\s\.\-\/]+?)\s+([MF])\s+(.+)$',
        re.IGNORECASE
    )

    for linha in linhas:
        linha_limpa = linha.strip()
        if not linha_limpa or "RELAÇÃO DOS LOTES" in linha_limpa.upper() or "LOTE QTDE VENDEDOR" in linha_limpa.upper():
            continue
        if "TOTAL MACHO" in linha_limpa.upper() or "COMISSÃO" in linha_limpa.upper():
            continue

        match = linha_regex.match(linha_limpa)
        if match:
            lote = match.group(1).strip()
            qtde = match.group(2).strip()
            vendedor = match.group(3).strip()
            sx = match.group(4).strip().upper()
            resto = match.group(5).strip()

            # Separar Descrição de Possível Observação
            # Observações geralmente vêm após o padrão de idade ('XX MS')
            obs = ""
            desc = resto
            match_ms = re.search(r'^(.*?\b\d+\s*(?:MS|MESES)\b)(.*)$', resto, re.IGNORECASE)
            if match_ms:
                desc = match_ms.group(1).strip()
                obs = match_ms.group(2).strip()

            lote_formatado = formatar_lote_para_planilha(lote, qtde, vendedor, sx, desc, obs)
            lotes.append(lote_formatado)

    return lotes
