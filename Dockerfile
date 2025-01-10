FROM python:3.12-slim as builder

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

COPY ./src ./src
COPY ./main.py ./main.py
COPY ./pyproject.toml ./pyproject.toml
COPY ./mq_files/linux ./mq_files/linux
COPY ./requirements.txt ./requirements.txt

RUN mkdir -p /opt/mqm
RUN cp -r ./mq_files/linux/* /opt/mqm/

# Fix for LD_LIBRARY_PATH
ENV LD_LIBRARY_PATH=/app/mq_files/linux/lib64:/opt/mqm/lib64

# Download and install dependencies
RUN pip install --upgrade pip && \
    pip install wheel  && \
    pip install -r requirements.txt

FROM python:3.12-slim

WORKDIR /app

ENV LD_LIBRARY_PATH=/app/mq_files/linux/lib64:/opt/mqm/lib64

# Copy only necessary files from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /opt/mqm /opt/mqm
COPY ./src ./src
COPY ./main.py ./main.py
COPY ./pyproject.toml ./pyproject.toml
COPY ./mq_files/linux ./mq_files/linux

CMD ["python", "main.py"]