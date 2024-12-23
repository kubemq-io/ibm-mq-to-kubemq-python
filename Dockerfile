FROM python:3.13-slim

WORKDIR /app

# Install build dependencies including curl
RUN apt-get update && apt-get install -y \
    git \
    gcc \
    g++ \
    python3-dev \
    make \
    cmake \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Download the latest installer
ADD https://astral.sh/uv/install.sh /uv-installer.sh

# Run the installer then remove it
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Ensure the installed binary is on the `PATH`
ENV PATH="/root/.local/bin/:$PATH"

COPY ./src ./src
COPY ./main.py ./main.py
COPY ./pyproject.toml ./pyproject.toml
COPY ./mq_files/linux ./mq_files/linux

RUN mkdir -p /opt/mqm
RUN cp -r ./mq_files/linux/* /opt/mqm/

# Set the LD_LIBRARY_PATH environment variable in the Dockerfile
ENV LD_LIBRARY_PATH=/app/mq_files/linux/lib64:/opt/mqm/lib64:$LD_LIBRARY_PATH

RUN uv sync

CMD ["uv","run","main.py"]