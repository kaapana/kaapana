FROM python:3.9-alpine

RUN python3 -m pip install --upgrade pip && python3 -m pip install selenium==4.2.0

COPY files/src/ src/
COPY files/tests/ tests/
