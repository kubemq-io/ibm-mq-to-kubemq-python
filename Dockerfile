FROM python:3.13-slim as builder

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

ENV LD_LIBRARY_PATH=/app/mq_files/linux/lib64:/opt/mqm/lib64:$LD_LIBRARY_PATH

RUN uv sync

FROM python:3.13-slim

WORKDIR /app

# Create the directory where uv will be copied to
RUN mkdir -p /root/.local/bin

# Copy uv binary from builder stage
COPY --from=builder /root/.local/bin/uv /root/.local/bin/
COPY --from=builder /root/.local/bin/uvx /root/.local/bin/

ENV PATH="/root/.local/bin/:$PATH"
ENV LD_LIBRARY_PATH=/app/mq_files/linux/lib64:/opt/mqm/lib64:$LD_LIBRARY_PATH

COPY --from=builder /app/.venv ./.venv
COPY ./src ./src
COPY ./main.py ./main.py
COPY ./pyproject.toml ./pyproject.toml
COPY ./mq_files/linux ./mq_files/linux

RUN mkdir -p /opt/mqm
RUN cp -r ./mq_files/linux/* /opt/mqm/

CMD ["uv","run","main.py"]