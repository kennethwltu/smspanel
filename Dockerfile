FROM python:3.12-slim

# Proxy configuration arguments
ARG PROXY_USER
ARG PROXY_PASSWORD
ARG PROXY_HOST
ARG PROXY_PORT

# Set environment variables for other tools (curl, wget, pip, etc.)
ENV HTTP_PROXY=http://${PROXY_USER}:${PROXY_PASSWORD}@${PROXY_HOST}:${PROXY_PORT}
ENV HTTPS_PROXY=http://${PROXY_USER}:${PROXY_PASSWORD}@${PROXY_HOST}:${PROXY_PORT}
ENV NO_PROXY=localhost,127.0.0.1,10.34.117.107,10.34.117.109,10.34.117.110,10.34.117.111,10.34.117.119,10.34.72.168,10.34.72.169,10.34.72.170,10.34.72.171,10.34.72.172,10.34.72.173,10.34.73.168,10.34.73.169,10.34.73.170,10.34.73.171,10.34.73.172,10.34.73.173,10.34.222.35
ENV http_proxy=http://${PROXY_USER}:${PROXY_PASSWORD}@${PROXY_HOST}:${PROXY_PORT}
ENV https_proxy=http://${PROXY_USER}:${PROXY_PASSWORD}@${PROXY_HOST}:${PROXY_PORT}
ENV no_proxy=localhost,127.0.0.1,10.34.117.107,10.34.117.109,10.34.117.110,10.34.117.111,10.34.117.119,10.34.72.168,10.34.72.169,10.34.72.170,10.34.72.171,10.34.72.172,10.34.72.173,10.34.73.168,10.34.73.169,10.34.73.170,10.34.73.171,10.34.73.172,10.34.73.173,10.34.222.35

# Create pip configuration
RUN mkdir -p /root/.pip && \
    echo '[global]' > /root/.pip/pip.conf && \
    echo "proxy = http://${PROXY_USER}:${PROXY_PASSWORD}@${PROXY_HOST}:${PROXY_PORT}" >> /root/.pip/pip.conf && \
    echo 'trusted-host = pypi.org files.pythonhosted.org' >> /root/.pip/pip.conf

# Create app directory and set permissions
WORKDIR /app

## Copy application code
COPY requirements.txt requirements.txt

# Install dependencies
RUN pip install -r requirements.txt

## Copy application code
COPY . .

# Install the smspanel package in development mode
RUN pip install -e .

# Set environment variables for other tools (curl, wget, pip, etc.)
ENV HTTP_PROXY=
ENV HTTPS_PROXY=
ENV NO_PROXY=
ENV http_proxy=
ENV https_proxy=
ENV no_proxy=

RUN rm -f /root/.pip/pip.conf

RUN pytest --cov=src --cov-report=term-missing

RUN ruff check .

# Default command
CMD ["python", "run.py"]
