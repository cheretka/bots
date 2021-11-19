from agent import Agent
from websockets import Websocket
import orjson
from websockets.typing import Data
import asyncio

async def start(game_code, player_name):
    async with Websocket(game_code, player_name) as web:
        while True:
            # Wait for state
            state: Data = await web.receive()
            # Update agent with state
            agent.set_env(orjson.loads(state))
            # Choose action
            action = agent.choose_action()
            # Send action
            await web.send(orjson.dumps(action).decode("utf-8"))
            # Update agent learning
            agent.update()


# Get game id 
print("Gimme game code ༼ つ ◕_◕ ༽つ")
game_code = input()
print("Now name (｡◕‿‿◕｡)")
player_name = input()

# Create agent
agent = Agent()

# Send request to the server to join a game
loop = asyncio.new_event_loop()
loop.run_until_complete(start())




