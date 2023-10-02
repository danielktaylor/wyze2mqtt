# wyze2mqtt

Talk to Wyze devices via MQTT. The heavy lifting is done by [wyze-sdk](https://github.com/shauntarves/wyze-sdk).

I've only added support for Wyze color bulbs, but it should be easy to add other devices if they're supported by wyze-sdk. The code is intentionally quite simple; I don't personally have a need for more complexity, because I don't have many Wyze devices.

This handles automatically refreshing the Wyze token.
