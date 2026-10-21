FROM python:3.11-slim
WORKDIR /app
COPY app.py consensus.py index.html ./
ENV AMOS_BIND=0.0.0.0 PORT=8765 PYTHONUNBUFFERED=1
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8765/healthz',timeout=3)"
CMD ["python","app.py"]
