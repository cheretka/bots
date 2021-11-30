from ..base import Agent
from .action import AgarntAction
import numpy as np

def euclidean_dist(x1,y1,x2,y2):
    return np.linalg.norm(np.array([x1,y1]), np.array([x2,y2]))

class CloseFoodAgent(Agent):
	
	def __init__(self, generator: np.random.Generator):
		super().__init__(AgarntAction)
		self.__rng = generator
  
	def choose_action(self) -> AgarntAction:
        
        # take a list of other players
            enemies = self.current_state['ps']
            player = self.current_state['p']

        # remove those bigger than you
            smaller_enemies = []
            for e in enemies:
                if e['r'] < player['r']:
                    smaller_enemies.append(e)
            # search for the nearest one - near_enemy
            near_enemy = smaller_enemies[0]
            for se in smaller_enemies:
                if euclidean_dist(se['x'],se['y'],player['x'],player['y']) < euclidean_dist(near_enemy['x'],near_enemy['y'],player['x'],player['y']):
                    near_enemy = se
            # search for the closest food - near_food
            foods = self.current_state['f']
            near_food = foods[0]
            for f in foods:
                if euclidean_dist(f['x'],f['y'],player['x'],player['y']) < euclidean_dist(near_food['x'],near_food['y'],player['x'],player['y']):
                    near_food = f
            # eating other player is more important than food, but food is also good
            near = near_enemy
            if euclidean_dist(near_enemy['x'],near_enemy['y'],player['x'],player['y'])/euclidean_dist(near_food['x'],near_food['y'],player['x'],player['y']) >= 1.5:
                near = near_food
            # check in what direction to go
            direction = {"L":False, "D":False, "R":False, "U":False}
            if near['x'] < player['x']:
                direction['U'] = True
            elif near['x'] > player['x']:
                direction['D'] = True
            if near['y'] < player['y']:
                direction['L'] = True
            elif near['y'] > player['y']:
                direction['R'] = True
                return self.action_provider.decode(direction)

	def handle_new_states(self, msg):
		self.current_state = msg
	
	@property
	def is_done(self) -> bool:
		if "d" in self.current_state:
			return self.current_state["d"]
		return False

	def update(self):
		...