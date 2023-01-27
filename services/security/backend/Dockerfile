FROM local-only/security-pages-frontend:latest as build-frontend

LABEL IMAGE="security-pages"
LABEL VERSION="0.0.0"
LABEL CI_IGNORE="False"

FROM python:3.10-slim

WORKDIR /security-pages

RUN apt update && apt install -y curl

COPY files/ ./
RUN chmod +x boot.sh
RUN pip install --no-cache-dir -r requirements.txt

COPY --from=build-frontend /dist/ ./static

EXPOSE 5000

#CMD tail -f /dev/null
ENTRYPOINT ["./boot.sh"]
