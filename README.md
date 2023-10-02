# wyze2mqtt

Talk to Wyze devices via MQTT. The heavy lifting is done by [wyze-sdk](https://github.com/shauntarves/wyze-sdk).

I've only added support for Wyze color bulbs, but it should be easy to add other devices if they're supported by wyze-sdk. The code is intentionally quite simple; I don't personally have a need for more complexity, because I don't have many Wyze devices. You'll probably need to modify it a bit for your own needs.

This handles automatically refreshing the Wyze token, and it has proven to be stable the last few weeks.
