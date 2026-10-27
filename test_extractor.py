from extractor import extrair_lotes_de_texto, parse_descricao

# Teste com linhas reais do OCR do leilão
sample_text = """
SN 190 FAZ SAO GERMANO M GARROTE(S) NELORE DE 16 MS
1 7 FAZ AGUAS MARINAS F BEZERRA(S) NELORE DE 12 MS FILHAS BOI PO JOAO MAURICIO 
012 14 FAZ JR M GARROTE(S) MESTIÇO DE 22 MS
101 1 FAZ CACHOEIRA F VACA(S) PARIDA(S) CRUZADA DE 48 MS PARIDA DE MACHO 
018 13 FAZ BACURI F BEZERRA(S) ANELORADA DE 13 MS
33 52 FAZ CAMPO LIMPO M BOI(S) NELORE DE 36 MS
404 4 FAZ CAIPIRA M GARROTE(S) NELORE DE 20 MS
500 5 AGRO RURAL VET M GARROTE(S) CRUZADO DE 18 MS
"""

lotes = extrair_lotes_de_texto(sample_text)
print(f"Total de lotes testados: {len(lotes)}")
for lote in lotes:
    print(lote)
