# Bot de Tickets — Discord (N MULTIMIDIA)

Bot de abertura de chamados para técnicos em campo. Ao clicar em **Abrir Ticket**,
o bot conduz o colaborador pelo fluxo de perguntas (conforme o fluxograma do cliente),
coleta textos e fotos, gera um **PDF** com todo o histórico e salva na estrutura de
pastas padronizada.

## O que já está implementado

- ✅ Botão **"Abrir Ticket"** (persistente — sobrevive a reinícios)
- ✅ Fluxo completo do fluxograma: UFMT, VMMT, IFT e Coordenação de Segurança, com todos os subtipos e perguntas
- ✅ Coleta de textos, números e **fotos** (uma ou várias por etapa)
- ✅ Pergunta **"Serviço concluído? (Sim/Não)"** onde o fluxo prevê
- ✅ Registro automático: colaborador (login), data/hora e **localização via EXIF da foto**
- ✅ Geração de **PDF** com metadados + respostas + fotos + transcrição da conversa
- ✅ Salvamento na hierarquia: `Categoria / Mês Ano / Tipo de Serviço / Dia / arquivo.pdf`
- ✅ Nome do PDF: `Dia_HoraMin_TipoServico_NomeColaborador.pdf`
- ✅ Comandos admin: `/painel`, `/listar`, `/fechar`

## Instalação

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # depois edite o .env
```

## Configuração do bot no Discord

1. Acesse o **Discord Developer Portal** → New Application.
2. Aba **Bot** → *Reset Token* → copie o token para `DISCORD_TOKEN` no `.env`.
3. Ainda em **Bot**, ative **Privileged Gateway Intents**:
   - *Server Members Intent*
   - *Message Content Intent*
4. Aba **OAuth2 → URL Generator**: marque `bot` e `applications.commands`.
   Permissões mínimas: *Manage Threads, Send Messages, Read Message History,
   Attach Files, Create Private Threads, Embed Links*.
5. Abra a URL gerada e adicione o bot ao servidor.

## Como usar

```bash
python bot.py
```

- Rode `/painel` no canal onde os técnicos vão abrir chamados.
- O técnico clica em **Abrir Ticket** → o bot cria uma thread privada e faz as perguntas.
- Ao final, o PDF é enviado na thread **e** salvo na pasta `STORAGE_ROOT`.

## Onde os arquivos são salvos

Definido por `STORAGE_ROOT` no `.env`:
- **Servidor físico:** aponte para um ponto de montagem de rede (ex: `/mnt/servidor/chamados`).
- **Google Drive / nuvem:** aponte para uma pasta sincronizada pelo *Google Drive para Desktop* ou por *rclone*.

## Deploy 24/7

### Opção A — systemd (VPS Linux, recomendado)

Crie `/etc/systemd/system/bot-tickets.service`:

```ini
[Unit]
Description=Bot de Tickets Discord
After=network.target

[Service]
WorkingDirectory=/opt/bot-tickets
ExecStart=/opt/bot-tickets/venv/bin/python bot.py
Restart=always
RestartSec=5
User=botuser

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now bot-tickets
sudo journalctl -u bot-tickets -f      # ver logs
```

### Opção B — Docker

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "bot.py"]
```

```bash
docker build -t bot-tickets .
docker run -d --restart=always --env-file .env -v /dados/chamados:/app/chamados bot-tickets
```

## Ajustar o fluxo de perguntas

Todo o fluxo fica em **`flow.py`**, num único dicionário fácil de editar.
Para adicionar/remover perguntas, basta mexer nas listas de etapas.
Tipos disponíveis: `text`, `number`, `photo` (use `"multiple": True` p/ várias),
`selfie`, `yesno`.

> Observação: o campo **"Número da OS"** foi adicionado nas OS de UFMT/VMMT porque
> aparece na descrição original do projeto, mas **não** estava no fluxograma. As
> linhas estão marcadas com `# [confirmar com o cliente]` — remova se ele não quiser.
