import asyncio, websockets, json

async def stream():

    uri="wss://stream.aisstream.io/v0/stream"

    async with websockets.connect(uri) as ws:

        await ws.send(json.dumps({
            "APIKey":"YOUR_KEY",
            "BoundingBoxes":[[[-90,-180],[90,180]]]
        }))

        async for msg in ws:
            data=json.loads(msg)
            print(data)

asyncio.run(stream())
