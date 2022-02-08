from time import sleep
from src import make_env, get_session_id, spawn_bots, RandomAgent, CloseFoodAgent, cleanup
import numpy as np
if __name__ == "__main__":
	gen= np.random.default_rng(2137)

# manager = spawn_bots("ws://localhost:2137", get_session_id(), RandomAgent, 1, generator=gen)

	manager = spawn_bots("ws://botbattles.iis.p.lodz.pl:2137", "session_434999395f3cd0f6", RandomAgent, 100, generator=gen)

	try:
		while True:
			sleep(0.1)
	except:...
	finally: manager.terminate(30)	
