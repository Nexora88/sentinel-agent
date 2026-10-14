FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/memory/personal /app/memory/universe /app/memory/universe_kb /app/memory/generated_images

EXPOSE 8000

CMD ["python", "-m", "scripts.run", "web", "--host", "0.0.0.0", "--port", "8000"]
