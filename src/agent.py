
import random
from typing import List

class Agent:
    def __init__(self, legal_actions: List):
        self.get_legal_actions = legal_actions
        self.is_learning = False

    # By default agent chooses random action
    def choose_action(self):
        return random.choice(self.get_legal_actions)

    # This is a function to update agent policy about 
    # choosing actions. Default agent chooses random action
    # and has learning turned off
    def update(self):
        if not self.is_learning:
            return
        # do some learning
    