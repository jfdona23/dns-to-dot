FROM python:slim

WORKDIR /app

COPY src/requirements.txt ./
RUN pip install -r requirements.txt

ENV LOGLEVEL "INFO"
ENV LISTEN_IP "0.0.0.0"
ENV LISTEN_PORT "53"
ENV PROTO "udp"
ENV BUFFER_SIZE "512"
ENV DNS_PROVIDER "cloudfare1"
ENV MULTIPROCESSING "True"

COPY src/* ./

ENTRYPOINT ["python", "/app/dns2dot.py"]