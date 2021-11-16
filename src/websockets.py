import asyncio
from websockets import connect


class Websocket:
    def __init__(self, game_code, player_name):
        self.game_code = game_code
        self.player_name = player_name

    async def __aenter__(self):
        self._conn = connect(f"ws://localhost:2137/join_to_game?session_id={self.game_code}?player_name={self.player_name}")
        self.websocket = await self._conn.__aenter__()        
        return self

    async def __aexit__(self, *args, **kwargs):
        await self._conn.__aexit__(*args, **kwargs)

    async def send(self, message):
        await self.websocket.send(message)

    async def receive(self):
        return await self.websocket.recv()
