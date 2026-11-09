FROM docker.io/python:3.12-slim

LABEL IMAGE="helm-chart-consumer-api-mock"
LABEL VERSION="0.1.0"
# This image only shows a proposed API and is not a platform component, so kaapana-build must not build or push it.
LABEL BUILD_IGNORE="True"

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app

USER 1000
EXPOSE 5055
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5055"]
