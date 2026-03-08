# Multi-stage build: python:3.11-slim → distroless
# Final image size: ~80MB

FROM python:3.11-slim AS builder

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Final stage: distroless (minimal, secure)
FROM gcr.io/distroless/python3.11:nonroot

WORKDIR /app

# Copy Python site-packages from builder
COPY --from=builder /root/.local /root/.local
# Copy app code
COPY . .

# Add local pip packages to PATH
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Run scanner as non-root user
USER nonroot

ENTRYPOINT ["python", "-m", "scanner.main"]
CMD ["--regions", "ap-south-1,us-east-1", "--output", "/app/findings.json"]
