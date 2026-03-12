FROM python:3.11-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scanner /app/scanner
COPY notifier /app/notifier
COPY ec2_pricing /app/ec2_pricing
COPY findings-mock.json /app/findings-mock.json

FROM gcr.io/distroless/python3-debian12:nonroot

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app /app

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/opt/venv/lib/python3.11/site-packages:/app"

USER nonroot:nonroot

ENTRYPOINT ["python", "-m", "scanner.main"]
CMD ["--regions", "ap-south-1,us-east-1", "--output", "/app/findings.json"]
