FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/home/app/.cache/huggingface

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --create-home app

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cpu \
        "torch>=2.3,<3" \
    && pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY scripts ./scripts
COPY benchmarks ./benchmarks
COPY evaluation ./evaluation
RUN mkdir -p /home/app/.cache /app/results \
    && chown -R app:app /app /home/app/.cache

USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
