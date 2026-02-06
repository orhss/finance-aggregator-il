FROM python:3.12-slim

WORKDIR /app

# Install uv, Chromium and minimal dependencies for headless operation
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH
ENV PATH="/root/.local/bin:$PATH"

# Tell Selenium to use system Chromium
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock* ./

# Install dependencies only (not the project itself)
RUN uv sync --no-dev --no-install-project --frozen 2>/dev/null || uv sync --no-dev --no-install-project

# Copy all content to the docker file
COPY . .

# Now install the project itself
RUN uv sync --no-dev

# Streamlit config
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["uv", "run", "streamlit", "run", "streamlit_app/main.py", "--server.port=8501", "--server.address=0.0.0.0"]
