FROM python:3.9-alpine

WORKDIR .
ADD alert_exporter.py .

RUN pip install prometheus-client

CMD ["python", "/tests/main.py"]