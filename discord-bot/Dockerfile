FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN --mount=type=secret,id=proxy_ca sh -c 'if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca; fi; pip install --no-cache-dir -r requirements.txt'
COPY bot.py .
CMD ["python", "bot.py"]
