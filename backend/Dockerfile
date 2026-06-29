FROM python:3.11-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libxml2-dev \
    libxslt-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Strip test-only packages (everything from the "# Test" comment onward)
# then apply the two-pass install to handle pinned langchain/crewai conflicts:
#   Pass 1 — full resolution for everything except the conflicting AI ecosystem
#   Pass 2 — --no-deps install for the pinned AI packages
RUN sed '/^# Test/,$ d' requirements.txt > /tmp/req_prod.txt \
    && grep -vE "^langchain|^crewai|^langgraph|^#" /tmp/req_prod.txt > /tmp/req_safe.txt \
    && pip install --no-cache-dir -r /tmp/req_safe.txt \
    && grep -E "^langchain|^crewai|^langgraph" /tmp/req_prod.txt > /tmp/req_ai.txt \
    && pip install --no-cache-dir --no-deps -r /tmp/req_ai.txt

COPY . .

RUN touch resume.txt

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
