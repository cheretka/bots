
# TODO front agarnt page component bool
LEFT,DOWN,RIGHT,UP = 0,1,2,3
LD,LU,RD,RU = 4,5,6,7

class Environment():
    legal_actions = [LEFT,DOWN,RIGHT,UP,LD,LU,RD,RU]

    def __init__(self, game_width = 200, game_height = 200):
        self.current_state = {}
        self.GAME_WIDTH = game_width
        self.GAME_HEIGHT = game_height


    def set_state(self, state):
        self.current_state = state
        self.player = state['player']
        self.enemies = state['players']
        self.foods = state['food']
        self.GAME_WIDTH = state['board'][0]
        self.GAME_HEIGHT = state['board'][1]


    def get_legal_actions(self):
        return self.legal_actions


    def get_player_position(self):
        return tuple(self.player['x'], self.player['y'])


    def get_player_size(self):
        return self.player['radius']

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






    
        

         

    
        