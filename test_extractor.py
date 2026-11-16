from extractor import extrair_lotes_de_texto

# Teste 1: Formato São Germano
sao_germano = """
SN 190 FAZ SAO GERMANO M GARROTE(S) NELORE DE 16 MS
1 7 FAZ AGUAS MARINAS F BEZERRA(S) NELORE DE 12 MS FILHAS BOI PO JOAO MAURICIO 
012 14 FAZ JR M GARROTE(S) MESTIÇO DE 22 MS
26 31 FAZ CABAÇA F NOVILHA(S) NELORE DE 22 MS
101 1 FAZ CACHOEIRA F
VACA(S) PARIDA(S) CRUZADA DE 48 
MS PARIDA DE MACHO 
"""

# Teste 2: Formato Boiadeiro Leilões
boiadeiro = """
01 30 FAZENDA SERRA GRANDE MACHO BEZERRO(S) NELORE DE 9 MS
25 17 FAZENDA LIMOEIRO MACHO GARROTE(S) CRUZ. INDUSTRIAL DE 16 
MS
80A 46 FAZENDA SOARES MACHO GARROTE(S) NELORE DE 22 MS
903 8 FAZENDA SANTO ANTONIO MACHO BEZERRO(S) CRUZ. INDUSTRIAL DE 12 MS
"""

lotes_sg = extrair_lotes_de_texto(sao_germano)
print(f"São Germano extraídos: {len(lotes_sg)} lotes")
for l in lotes_sg:
    print(" ", l["LOTE"], "|", l["QUANTIDADE"], "|", l["SEXO"], "|", l["raca"], "|", l["MESES"], "|", l["LOCAL"], "|", l["observacao"])

lotes_bd = extrair_lotes_de_texto(boiadeiro)
print(f"\nBoiadeiro extraídos: {len(lotes_bd)} lotes")
for l in lotes_bd:
    print(" ", l["LOTE"], "|", l["QUANTIDADE"], "|", l["SEXO"], "|", l["raca"], "|", l["MESES"], "|", l["LOCAL"], "|", l["observacao"])
