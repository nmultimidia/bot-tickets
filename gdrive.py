"""
Envio dos PDFs para uma pasta PRIVADA do Google Drive, recriando a mesma
hierarquia usada localmente:  Categoria / Mês Ano / Tipo de Serviço / Dia.

Usa uma CONTA DE SERVIÇO (service account) -> funciona 24/7, sem login manual.
Se GDRIVE_ENABLED=false no .env, o módulo não faz nada (o salvamento local
continua funcionando normalmente).

Setup resumido (detalhes na resposta):
  1. Criar um projeto no Google Cloud e ativar a "Google Drive API".
  2. Criar uma Conta de Serviço e baixar a chave JSON (service_account.json).
  3. Compartilhar a pasta do Drive com o e-mail da conta de serviço (como Editor).
  4. Preencher no .env: GDRIVE_ENABLED, GDRIVE_CREDENTIALS, GDRIVE_ROOT_FOLDER_ID.
"""
import os

from config import GDRIVE_ENABLED, GDRIVE_CREDENTIALS, GDRIVE_ROOT_FOLDER_ID

_service = None
_folder_cache = {}          # evita recriar/reprocurar pastas a cada chamado

_SCOPES = ["https://www.googleapis.com/auth/drive"]


def _get_service():
    global _service
    if _service is None:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        creds = service_account.Credentials.from_service_account_file(
            GDRIVE_CREDENTIALS, scopes=_SCOPES)
        _service = build("drive", "v3", credentials=creds, cache_discovery=False)
    return _service


def _pasta(service, nome, parent_id):
    """Procura a subpasta 'nome' dentro de parent_id; cria se não existir."""
    chave = (parent_id, nome)
    if chave in _folder_cache:
        return _folder_cache[chave]

    seguro = nome.replace("\\", "\\\\").replace("'", "\\'")
    q = (f"name = '{seguro}' and mimeType = 'application/vnd.google-apps.folder' "
         f"and '{parent_id}' in parents and trashed = false")
    resp = service.files().list(
        q=q, fields="files(id, name)", spaces="drive",
        supportsAllDrives=True, includeItemsFromAllDrives=True,
    ).execute()
    achados = resp.get("files", [])

    if achados:
        fid = achados[0]["id"]
    else:
        meta = {
            "name": nome,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        }
        fid = service.files().create(
            body=meta, fields="id", supportsAllDrives=True).execute()["id"]

    _folder_cache[chave] = fid
    return fid


def upload_pdf(caminho_local, subpastas):
    """
    caminho_local: caminho do PDF no disco.
    subpastas:     lista ordenada de nomes de pasta a partir da raiz do Drive,
                   ex: ["Abertura de OS - UFMT", "Julho 2026", "OS Instalação", "10"]
    Retorna o link (webViewLink) do arquivo no Drive, ou None se desabilitado.
    """
    if not GDRIVE_ENABLED:
        return None
    if not GDRIVE_ROOT_FOLDER_ID:
        raise RuntimeError("GDRIVE_ROOT_FOLDER_ID não configurado no .env")

    from googleapiclient.http import MediaFileUpload

    service = _get_service()

    parent = GDRIVE_ROOT_FOLDER_ID
    for nome in subpastas:
        parent = _pasta(service, nome, parent)

    media = MediaFileUpload(caminho_local, mimetype="application/pdf", resumable=True)
    meta = {"name": os.path.basename(caminho_local), "parents": [parent]}
    arquivo = service.files().create(
        body=meta, media_body=media, fields="id, webViewLink",
        supportsAllDrives=True,
    ).execute()
    return arquivo.get("webViewLink")
