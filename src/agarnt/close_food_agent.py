from ..base import Agent
from .action import AgarntAction
import numpy as np

def euclidean_dist(x1,y1,x2,y2):
    return np.linalg.norm(np.array([x1,y1]) - np.array([x2,y2]))

class CloseFoodAgent(Agent):
    
    def __init__(self, generator: np.random.Generator):
        super().__init__(AgarntAction)
        self.__rng = generator
  
    def choose_action(self) -> AgarntAction:
        if self.current_state:
        # take a list of other players
            enemies = self.current_state['ps']
            player = self.current_state['p']

        # remove those bigger than you
            smaller_enemies = []
            for e in enemies:
                if e['r'] < player['r']:
                    smaller_enemies.append(e)
            # search for the nearest one - near_enemy
            near_enemy = next(iter(smaller_enemies), None)
            for se in smaller_enemies:
                if euclidean_dist(se['x'],se['y'],player['x'],player['y']) < euclidean_dist(near_enemy['x'],near_enemy['y'],player['x'],player['y']):
                    near_enemy = se
            # search for the closest food - near_food
            foods = self.current_state['f']
            near_food = next(iter(foods), None)
            for f in foods:
                if euclidean_dist(f[0],f[1],player['x'],player['y']) < euclidean_dist(near_food[0],near_food[1],player['x'],player['y']):
                    near_food = f
            if near_food:
                near_food = {'x':near_food[0], 'y': near_food[1]}
            # eating other player is more important than food, but food is also good
            near = near_enemy if near_enemy is not None else near_food
            if near_enemy and near_food and euclidean_dist(near_enemy['x'],near_enemy['y'],player['x'],player['y'])/euclidean_dist(near_food['x'],near_food['y'],player['x'],player['y']) >= 1.5:
                near = near_food
            # check in what direction to go
            direction = {"L":False, "D":False, "R":False, "U":False}
            if near:
                if near['x'] < player['x']:
                    direction['L'] = True
                elif near['x'] > player['x']:
                    direction['R'] = True
                if near['y'] < player['y']:
                    direction['D'] = True
                elif near['y'] > player['y']:
                    direction['U'] = True
                if not np.any(list(direction.values())): direction['U'] = True
                return self.action_provider.decode({"directions":direction})
        return self.__rng.choice(self.action_provider.get_all())
    def handle_new_states(self, msg):
        #print(f"Received new state: {msg}s")
        self.current_state = msg
    
    @property
    def is_done(self) -> bool:
        if "d" in self.current_state:
            return self.current_state["d"]
        return False

    def update(self):
        ...