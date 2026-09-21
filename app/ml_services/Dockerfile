# python:3.11 matches the interpreter the shipped artifacts were trained with
# (pickle compatibility is scoped per sklearn version; keep both pinned).
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 MODEL_DIR=/app/models
WORKDIR /app
RUN addgroup --system app && adduser --system --ingroup app app

COPY pyproject.toml constraints.txt ./
COPY src ./src

# constraints.txt pins the EXACT versions the shipped joblib artifacts were
# trained with (scikit-learn 1.9.1, numpy 2.4.6, scipy 1.17.1, joblib 1.6.0).
# sklearn joblib pickles are not guaranteed to load or predict identically
# across minor versions — always install against the captured constraints.
RUN pip install --no-cache-dir -c constraints.txt .

COPY config ./config
COPY models ./models
RUN mkdir -p /app/models && chown -R app:app /app
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/health', timeout=3)" || exit 1
CMD ["uvicorn", "ml_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
