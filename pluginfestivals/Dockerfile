FROM ghcr.io/home-assistant/base:latest

RUN apk update && \
    apk add --no-cache bluez python3 py3-pip

COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

WORKDIR /

COPY fridge.py fridge_mqtt_bridge.py ./

# Copy data for app
COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]