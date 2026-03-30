# HEARTBEAT.md

## Silent Mode (Do Not Push)

When heartbeat polling is triggered:

1. Do not send any proactive message to WeChat or any other channel.
2. Do not send placeholder texts such as `HEARTBEAT_OK` or `心跳正常`.
3. Only send a message if there is a critical emergency that requires immediate human action.

If there is no critical emergency, return no outbound user-facing message.
