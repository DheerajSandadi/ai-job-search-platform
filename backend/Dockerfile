FROM python:3.11-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libxml2-dev \
    libxslt-dev \
    curl \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Two-pass install to work around pinned langchain/crewai version conflicts:
# Pass 1 — install everything except the conflicting ecosystem with full dep
#           resolution so transitive deps (click, starlette, etc.) are present.
# Pass 2 — install the conflicting packages with --no-deps so pip's resolver
#           doesn't reject the pinned versions.
RUN grep -vE "^langchain|^crewai|^langgraph" requirements.txt > /tmp/req_safe.txt \
    && pip install --no-cache-dir -r /tmp/req_safe.txt \
    && grep -E "^langchain|^crewai|^langgraph" requirements.txt > /tmp/req_ai.txt \
    && pip install --no-cache-dir --no-deps -r /tmp/req_ai.txt

COPY . .

RUN touch resume.txt

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
