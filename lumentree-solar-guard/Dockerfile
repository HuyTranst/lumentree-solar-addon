ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM $BUILD_FROM

RUN apk add --no-cache python3 py3-requests py3-paho-mqtt

COPY solar_ac_daemon.py /
COPY run.sh /

RUN chmod +x /run.sh

CMD [ "/run.sh" ]
