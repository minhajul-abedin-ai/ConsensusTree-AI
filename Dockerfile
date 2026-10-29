FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE /app/
COPY src /app/src
RUN pip install --no-cache-dir . && useradd --create-home --uid 10001 council
USER council
WORKDIR /workspace
ENTRYPOINT ["consensustree"]
CMD ["--help"]
