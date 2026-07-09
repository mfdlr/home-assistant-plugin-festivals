FROM ghcr.io/home-assistant/base:latest

RUN apk update && \
    apk add --no-cache bluez python3 py3-pip

#RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

WORKDIR /

COPY fridge.py fridge_mqtt_bridge.py . 

CMD [ "python", "fridge_mqtt_bridge.py" ]
