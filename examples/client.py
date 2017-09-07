import asyncio
import ssl

import websockets


async def hello():
    await asyncio.sleep(1)
    context = ssl.create_default_context(cafile='/trusted_root.crt')
    context.load_cert_chain('/certificate.crt', keyfile='/certificate.key')
    connstr = 'wss://127.0.0.1:443'
    async with websockets.connect(connstr, ssl=context) as websocket:
        name = 'Greg'
        await websocket.send(name)
        print("> {}".format(name))

        greeting = await websocket.recv()
        print("< {}".format(greeting))

asyncio.get_event_loop().run_until_complete(hello())
