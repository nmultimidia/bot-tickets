FROM python:3.12-slim

WORKDIR /app

# Dependências do sistema (fuso horário correto + libs de imagem para Pillow/reportlab)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata libjpeg62-turbo zlib1g \
    && rm -rf /var/lib/apt/lists/*
ENV TZ=America/Sao_Paulo

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Os volumes (chamados/, token.json, service_account.json, client_secret.json,
# log_config.json) são gerenciados pelo docker-compose.yml via bind mount
# com caminho absoluto — não precisam ser declarados aqui.

CMD ["python", "bot.py"]
