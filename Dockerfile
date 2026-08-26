FROM python:3.12-slim AS builder

WORKDIR /app
COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir -e .

COPY src/ src/
COPY data/ data/

FROM python:3.12-slim AS runtime

RUN groupadd -r clawforge && useradd -r -g clawforge clawforge
WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app/src src/
COPY --from=builder /app/pyproject.toml .

RUN mkdir -p /app/data && chown -R clawforge:clawforge /app/data

USER clawforge

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/v1/health').raise_for_status()"

CMD ["uvicorn", "clawforge.main:app", "--host", "0.0.0.0", "--port", "8000"]
