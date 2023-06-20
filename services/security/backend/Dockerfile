FROM local-only/security-pages-frontend:latest as build-frontend

LABEL IMAGE="security-pages"
LABEL VERSION="latest"
LABEL CI_IGNORE="False"

FROM local-only/base-python-cpu:latest

WORKDIR /security-pages

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*


COPY files/ ./
RUN chmod +x boot.sh

#activate virtual env
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip install --no-cache-dir -r requirements.txt --disable-pip-version-check

COPY --from=build-frontend /dist/ ./static

EXPOSE 5000

#CMD tail -f /dev/null
ENTRYPOINT ["./boot.sh"]
