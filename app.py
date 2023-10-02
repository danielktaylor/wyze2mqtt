import asyncio
import json
import logging
import aiomqtt
import os
from wyze_sdk import Client
from wyze_sdk.errors import WyzeApiError


# configuration

WYZE_EMAIL = os.environ['WYZE_EMAIL']
WYZE_PASSWORD = os.environ['WYZE_PASSWORD']
WYZE_KEY_ID = os.environ['WYZE_KEY_ID']
WYZE_API_KEY = os.environ['WYZE_API_KEY']
MQTT_BROKER = os.environ['MQTT_BROKER_HOST']

# Debugging
# logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(level=logging.INFO)

# Wyze

wyze_client = None
device_list = []

def wyze_login():
    global wyze_client
    logging.info("Starting Wyze login...")
    response = Client().login(
        email=WYZE_EMAIL,
        password=WYZE_PASSWORD,
        key_id=WYZE_KEY_ID,
        api_key=WYZE_API_KEY
    )
    
    wyze_access_token = response['access_token'];
    wyze_refresh_token = response['refresh_token'];
    wyze_client = Client(token=wyze_access_token, refresh_token=wyze_refresh_token)
    logging.info("Wyze login complete.")

async def wyze_refresh():
    while True:
        await asyncio.sleep(3600) # 1 hour
        logging.info("Refreshing Wyze API token...")
        response = wyze_client.refresh_token()
        wyze_client._token = response["data"]["access_token"]
        wyze_client._refresh_token = response["data"]["refresh_token"]

async def turn_bulb_on(client, device_mac, bulb_brightness, color_temp):
    device_model = 'WLPA19C'
    if bulb_brightness and color_temp:
        logging.debug("Turning bulb on with specific brightness & temperature")
        client.bulbs.set_brightness(device_mac=device_mac, device_model=device_model, brightness=bulb_brightness)
        client.bulbs.set_color_temp(device_mac=device_mac, device_model=device_model, color_temp=color_temp)
    else:
        logging.debug("Turning bulb on")
        client.bulbs.turn_on(device_mac=device_mac, device_model=device_model)

async def turn_bulb_off(client, device_mac):
    logging.debug("Turning bulb off")
    device_model = 'WLPA19C'
    client.bulbs.turn_off(device_mac=device_mac, device_model=device_model)

async def toggle_bulb(client, device_mac, bulb_brightness, color_temp):
    bulb = client.bulbs.info(device_mac=device_mac)
    if bulb.is_on:
        logging.debug("Toggling bulb state to off")
        client.bulbs.turn_off(device_mac=bulb.mac, device_model=bulb.product.model)
    else:
        logging.debug("Toggling bulb state to on")
        await turn_bulb_on(client, bulb.mac, bulb_brightness, color_temp)

def get_device_list(client):
    global device_list
    try:
        response = wyze_client.devices_list()
        for device in response:
            device_list.append(json.dumps(device.to_dict()))
    except WyzeApiError as e:
        logging.error(f"Error getting the device list from Wyze: {e}")


# MQTT

published_device_list = False

async def mqtt_publish(mqtt_client, topic, message):
    await mqtt_client.publish(topic, payload=message)

async def handle_message(device_mac, payload):
    try:
        json_msg = json.loads(payload)

        if json_msg['state'].strip() == 'on':
            await turn_bulb_on(wyze_client, device_mac, json_msg.get('brightness'), json_msg.get('temperature'))
        elif json_msg['state'].strip() == 'off':
            await turn_bulb_off(wyze_client, device_mac)
        elif json_msg['state'].strip() == 'toggle':
            await toggle_bulb(wyze_client, device_mac, json_msg.get('brightness'), json_msg.get('temperature'))
    except Exception as e:
        logging.error("Failed to decode message: " + repr(e))

async def listen():
    client = aiomqtt.Client(MQTT_BROKER)
    interval = 5  # Seconds
    logging.info("Started MQTT listener.")
    while True:
        try:
            async with client:
                if not published_device_list:
                    for device in device_list:
                        await mqtt_publish(client, "zigbee2mqtt/devices", device)
                    published_devoce_list = True

                async with client.messages() as messages:
                    # MQTT wildcard syntax:
                    # https://cedalo.com/blog/mqtt-topics-and-mqtt-wildcards-explained/
                    await client.subscribe("wyze2mqtt/+/set")
                    async for message in messages:
                        logging.debug(f"[{message.topic}] {message.payload}")
                        if message.topic.matches("wyze2mqtt/+/set"):
                            device_mac = str(message.topic).split("/")[1]
                            await handle_message(device_mac, message.payload)
        except aiomqtt.MqttError:
            logging.info(f"Connection lost; Reconnecting in {interval} seconds ...")
            await asyncio.sleep(interval)

async def main():
    async with asyncio.TaskGroup() as tg:
        tg.create_task(wyze_refresh())  # Start the Wyze token refresher
        tg.create_task(listen())        # Start the MQTT listener

wyze_login()
get_device_list(wyze_client)
asyncio.run(main())
