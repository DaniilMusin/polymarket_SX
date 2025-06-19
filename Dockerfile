FROM python:3.11-slim

# Install deps early so Docker layer can be cached
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /app
COPY . .

CMD ["python", "main.py"]
