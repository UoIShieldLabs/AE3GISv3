FROM python:3.12-slim

# Docker CLI: Kathara talks to the daemon via the mounted socket, and the
# interactive terminal bridge uses `docker exec`. No ContainerLab, no sudo.
# buildx builds node images from Dockerfiles (BuildKit); git fetches the
# repositories those Dockerfiles live in. The host only needs Docker.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates curl git gnupg iproute2 && \
    install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc && \
    chmod a+r /etc/apt/keyrings/docker.asc && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo $VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends docker-ce-cli docker-buildx-plugin && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--timeout-graceful-shutdown", "5"]
