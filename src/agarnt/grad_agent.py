from ..base import Agent
from .action import AgarntAction
import numpy as np
import math

class GradAgent(Agent):
	
	def __init__(self, generator: np.random.Generator):
		super().__init__(AgarntAction)
		self.__rng = generator
		self.last_dir = {"L":True, "D":False, "R":False, "U":False}
  
	def choose_action(self) -> AgarntAction:
		if self.current_state:
			size = self.current_state['b']

			Z = np.zeros(size)
			ring_size = 40
			radius = 20
			food_z = self.makeGaussian(ring_size, fwhm=radius, center=(20,20), height=-1)
			foods = self.current_state['f']

			for f in foods:
				start_x = f[0]-radius if f[0]-radius > 0 else 0
				end_x = f[0]+radius if f[0]+radius < size[0] else size[0]
				start_y = f[1]-radius if f[1]-radius > 0 else 0
				end_y = f[1]+radius if f[1]+radius < size[1] else size[1]

				s_x = 0 if f[0]-radius > 0 else radius-f[0]
				e_x = ring_size if f[0]+radius < size[0] else size[0]-f[0]+radius
				s_y = 0 if f[1]-radius > 0 else radius-f[1]
				e_y = ring_size if f[1]+radius < size[1] else size[1]-f[1]+radius
				Z[start_x:end_x,start_y:end_y] += food_z[s_x:e_x,s_y:e_y]

			other_players = self.current_state['ps']

			for p in other_players:
				if self.current_state['p']['r'] <= p['r']:
					Z = Z + self.makeGaussian(size[0], fwhm=2*p['r'], center=(p['x'],p['y']), height=5)
				else:
					Z = Z + self.makeGaussian(size[0], fwhm=15*p['r'], center=(p['x'],p['y']), height=-5)
			
			directions = ['L', 'R', 'U', 'D', 'LU', 'LD', 'RU', 'RD']
			potentials = []
			for d in directions:
				x_n,y_n = self.current_state['p']['x'], self.current_state['p']['y']
			
				if 'U' in d:
					y_n += self.get_velocity(20, self.current_state['p']['r']) * self.current_state['delta'] + self.current_state['p']['r']
					y_n = math.ceil(y_n)
				if 'D' in d:
					y_n -= self.get_velocity(20, self.current_state['p']['r']) * self.current_state['delta'] + self.current_state['p']['r']
					y_n = math.ceil(y_n)
				if 'L' in d:
					x_n -= self.get_velocity(20, self.current_state['p']['r']) * self.current_state['delta'] + self.current_state['p']['r']
					x_n = math.ceil(x_n)
				if 'R' in d:
					x_n += self.get_velocity(20, self.current_state['p']['r']) * self.current_state['delta'] + self.current_state['p']['r']
					x_n = math.ceil(x_n)

				potentials.append(Z[x_n,y_n])
			minimal_potential = min(range(len(potentials)), key=potentials.__getitem__)
			if potentials[minimal_potential] == 0.0:
				# last dir
				return self.action_provider.decode({"directions":self.last_dir})
			dir = directions[minimal_potential]
			direction = {"L":False, "D":False, "R":False, "U":False}
			if 'L' in dir: direction['L'] = True
			elif 'R' in dir: direction['R'] = True
			if 'D' in dir: direction['D'] = True
			elif 'U' in dir: direction['U'] = True
			self.last_dir = direction
			return self.action_provider.decode({"directions":direction})

		print("Random action is chosen instead")
		return self.__rng.choice(self.action_provider.get_all())

	def handle_new_states(self, msg):
		self.current_state = msg

	def get_velocity(self, max_velocity, radius):
		log_value = np.log(radius) + 1
        # conversion to Python's float is necessary because np.log returns np.float64 object which is non-serializable
		return float(max_velocity - max(0, min(log_value, max_velocity - 1))) # clamp


	def makeGaussian(self, size, fwhm = 3, center=None, height=1):
		x = np.arange(0, size, 1, float)
		y = x[:,np.newaxis]

		if center is None:
			x0 = y0 = size // 2
		else:
			x0 = center[0]
			y0 = center[1]

		return height * np.exp(-4*np.log(2) * ((x-x0)**2 + (y-y0)**2) / fwhm**2)
	
	@property
	def is_done(self) -> bool:
		if "d" in self.current_state:
			return self.current_state["d"]
		return False

	def update(self):
		...