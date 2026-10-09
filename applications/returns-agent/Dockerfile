# Build from the repository root:  docker build -f applications/returns-agent/Dockerfile .
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
COPY pyproject.toml README.md ./
COPY platform ./platform
RUN pip install --no-cache-dir ".[azure]"
COPY applications/returns-agent ./applications/returns-agent
RUN pip install --no-cache-dir ./applications/returns-agent
RUN useradd --uid 10001 --no-create-home app
USER app
EXPOSE 8000
CMD ["uvicorn", "returns_agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
