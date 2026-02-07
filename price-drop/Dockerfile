FROM python:3.12-slim

WORKDIR /app

COPY . .

RUN groupadd -r -g 1000 appuser && useradd -r -u 1000 -g appuser appuser \
    && pip install --no-cache-dir -r requirements.txt \
    && mkdir -p /var/log/price-drop /opt/price-drop \
    && chown -R appuser:appuser /var/log/price-drop /opt/price-drop /app

USER appuser

ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py
ENV PORT=5000

EXPOSE $PORT

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "60", "--access-logfile", "/dev/null", "--error-logfile", "-", "app:app"]