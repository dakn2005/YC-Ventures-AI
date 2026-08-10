FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# CPU-only torch wheel first -- sentence-transformers otherwise pulls the full CUDA
# build (2GB+), which was timing out on download here and isn't needed for inference.
RUN pip install --no-cache-dir --default-timeout=180 torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir --default-timeout=180 -r requirements.txt

RUN python -m nltk.downloader stopwords punkt punkt_tab

COPY . .

EXPOSE 8000

CMD ["chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "8000"]
