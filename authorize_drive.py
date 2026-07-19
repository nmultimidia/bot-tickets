"""
Autoriza o bot a gravar no Google Drive de QUEM fizer o login aqui.
Rode UMA vez. Faça o login com a conta do CLIENTE (a que tem o espaço e a
pasta de destino), para os arquivos caírem no Drive dele.

Gera token.json (com o refresh token). Escopo 'drive' completo -> permite
gravar dentro de uma pasta já existente (a que o cliente definiu).

Pré-requisitos:
  - client_secret.json na mesma pasta (Google Cloud > Credenciais >
    ID do cliente OAuth > Tipo: App para computador).
  - pip install google-auth-oauthlib

Num VPS sem navegador, use um túnel SSH:
  1. No PC:  ssh -L 8080:localhost:8080 root@SEU_IP_DO_VPS
  2. No VPS: python authorize_drive.py
  3. Abra o link mostrado NO NAVEGADOR DO PC e autorize com a conta do cliente.
     (Se aparecer "app não verificado": Avançado > Acessar (não seguro).)
  4. token.json é criado no VPS. Pronto.
"""
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive"]

flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
creds = flow.run_local_server(
    port=8080,
    open_browser=False,
    authorization_prompt_message="Abra este link no navegador do PC:\n\n{url}\n",
    success_message="Autorização concluída! Pode fechar esta aba.",
)
with open("token.json", "w") as f:
    f.write(creds.to_json())
print("\ntoken.json gerado. O bot já pode gravar no Drive dessa conta.")
