"""
Organização e gravação dos arquivos no disco, seguindo EXATAMENTE
a hierarquia definida pelo cliente:

  [Bloco/Categoria] / [Mês Ano] / [Tipo de Serviço] / [Dia] / arquivo.pdf

Nome do PDF:
  [Dia]_[HoraMin]_[TipoServico]_[NomeColaborador].pdf
  ex: 10_1432_OSInstalacao_JoaoSilva.pdf
"""
import os
from datetime import datetime

from config import STORAGE_ROOT, MESES, camel


def componentes_pasta(categoria: str, subtipo: str, quando: datetime):
    """Devolve a lista ordenada de subpastas: [categoria, mês, tipo, dia].
    Usada tanto no disco local quanto para recriar a árvore no Google Drive."""
    mes = f"{MESES[quando.month]} {quando.year}"
    dia = quando.strftime("%d")
    return [categoria, mes, subtipo, dia]


def montar_caminho(categoria: str, subtipo: str, colaborador: str, quando: datetime):
    """Cria (se necessário) as pastas e devolve o caminho completo do PDF."""
    comps = componentes_pasta(categoria, subtipo, quando)
    pasta = os.path.join(STORAGE_ROOT, *comps)
    os.makedirs(pasta, exist_ok=True)

    dia = quando.strftime("%d")
    nome = f"{dia}_{quando.strftime('%H%M')}_{camel(subtipo)}_{camel(colaborador)}.pdf"
    return os.path.join(pasta, nome)


def listar_chamados(categoria: str = None, mes: str = None):
    """Lista PDFs salvos, opcionalmente filtrando por categoria e/ou mês."""
    encontrados = []
    if not os.path.isdir(STORAGE_ROOT):
        return encontrados
    for cat in sorted(os.listdir(STORAGE_ROOT)):
        if categoria and cat != categoria:
            continue
        cam_cat = os.path.join(STORAGE_ROOT, cat)
        if not os.path.isdir(cam_cat):
            continue
        for m in sorted(os.listdir(cam_cat)):
            if mes and m != mes:
                continue
            for raiz, _, arquivos in os.walk(os.path.join(cam_cat, m)):
                for a in arquivos:
                    if a.lower().endswith(".pdf"):
                        encontrados.append(os.path.join(raiz, a))
    return encontrados
