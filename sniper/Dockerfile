FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY sniper/ ./sniper/
COPY config/ ./config/
RUN mkdir -p state
# Par défaut : boucle de surveillance. Pour le serveur webhooks :
#   docker run ... sniper python -m sniper.webhook_server
CMD ["python", "-m", "sniper.runner", "--config", "config/watches.yaml"]
