
import random
from typing import List

LEFT,DOWN,RIGHT,UP = 0,1,2,3
LD,LU,RD,RU = 4,5,6,7

class Agent:
    def __init__(self, game_width = 200, game_height = 200):
        self.legal_actions = [LEFT,DOWN,RIGHT,UP,LD,LU,RD,RU]
        self.is_learning = False
        self.current_state = {}
        self.GAME_WIDTH = game_width
        self.GAME_HEIGHT = game_height
        self.set_env({'player':None,'players':None,'food':None,'board':None})

    # By default agent chooses random action
    def choose_action(self):
        return self.parse_action(random.choice(self.legal_actions))

    # This is a function to update agent policy about 
    # choosing actions. Default agent chooses random action
    # and has learning turned off
    def update(self):
        if not self.is_learning:
            return
        # do some learning
    
    def set_env(self, state):
        self.current_state = state
        self.player = state['player']
        self.enemies = state['players']
        self.foods = state['food']
        self.GAME_WIDTH = state['board'][0]
        self.GAME_HEIGHT = state['board'][1]

    def parse_action(self, action):
        directions = {}
        if action == UP or action == DOWN or action == RIGHT or action == LEFT:  
            directions[action] = True
        else:
            if action == LD:
                directions['LEFT'] = True
                directions['DOWN'] = True
            elif action == LU:
                directions['LEFT'] = True
                directions['UP'] = True
            elif action == RD:
                directions['RIGHT'] = True
                directions['DOWN'] = True
            elif action == RU:
                directions['RIGHT'] = True
                directions['UP'] = True
        return directions