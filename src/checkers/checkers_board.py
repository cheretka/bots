import copy
from copy import deepcopy
from typing import Any, Dict

class CheckersBoard:

    def __init__(self, state: Dict[str, Dict[str, bool]]):

        self.board = state['board']
        self.current_player = state['player']

        self.steps_without_hitting = {"r": 0, "a": 0}

        self.last_move = state['last_move']
        self.game_status = state['game_status']
        self.chosen_move = None



    def get_win(self):

        if self.steps_without_hitting["a"] >= 10 and self.steps_without_hitting["r"] >= 10:
            return 'remis'

        if self.steps_without_hitting["r"] == -1:
            return 'a'

        if self.steps_without_hitting["a"] == -1:
            return 'r'

        if len(self.get_possible_moves()) == 0:
            return 'a' if self.current_player == 'r' else 'r'

        return None


    def make_move(self, move):

        newState = deepcopy(self)
        for index in range(len(move) - 1):

            start_x = move[index][0]
            start_y = move[index][1]
            end_x = move[index + 1][0]
            end_y = move[index + 1][1]

            newState.board[end_x][end_y] = newState.board[start_x][start_y]

            if (end_x == (len(newState.board) - 1) and newState.board[end_x][end_y] == 'r') or (end_x == 0 and newState.board[end_x][end_y] == 'a'):
                newState.board[end_x][end_y] = newState.board[end_x][end_y].upper()

            newState.board[start_x][start_y] = ' '

            if abs(end_x - start_x) == 2:
                newState.board[(end_x + start_x) // 2][(end_y + start_y) // 2] = ' '
                newState.steps_without_hitting[newState.get_current_player()] = 0
            else:
                newState.steps_without_hitting[newState.get_current_player()] += 1

        newState.current_player = 'a' if newState.current_player == 'r' else 'r'

        newState.last_move = move

        return newState


    def get_possible_moves(self):

        delta = [[-1, -1], [-1, 1], [1, -1], [1, 1]] if self.current_player == 'a' else [
            [1, -1], [1, 1], [-1, -1], [-1, 1]]

        list_jump_moves = self.get_possible_multi_jump_moves()
        if len(list_jump_moves) > 0:
            return list_jump_moves

        list_simple_moves = []

        for x in range(len(self.board)):
            for y in range(len(self.board[x])):

                if self.board[x][y].lower() == self.current_player:

                    for index in range(4):

                        if self.board[x][y].islower() and index >= 2:
                            continue

                        new_x = x + delta[index][0]
                        new_y = y + delta[index][1]
                        if 0 <= new_x < len(self.board) and 0 <= new_y < len(self.board[x]) and self.board[new_x][new_y] == ' ':
                            list_simple_moves.append([[x, y], [new_x, new_y]])

        return list_simple_moves


    def get_possible_multi_jump_moves(self):

        list_jump_moves = []

        for x in range(len(self.board)):
            for y in range(len(self.board[x])):

                if self.board[x][y].lower() == self.current_player:

                    list_of_moves_1 = self.get_possible_jump_for_position(x, y,
                                                                          self.get_current_player())
                    all_lists = []

                    if len(list_of_moves_1) == 0:
                        continue

                    for move1 in list_of_moves_1:

                        new_chekers = self.make_move(move1)
                        list_of_moves_2 = new_chekers.get_possible_jump_for_position(
                            move1[1][0], move1[1][1], self.get_current_player())

                        if len(list_of_moves_2) == 0:
                            all_lists.append(move1)
                            continue

                        for move2 in list_of_moves_2:
                            move_1_2 = copy.deepcopy(move1)
                            move_1_2.append(move2[1])

                            new_chekers2 = new_chekers.make_move(move2)
                            list_of_moves_3 = new_chekers2.get_possible_jump_for_position(
                                move2[1][0], move2[1][1], self.get_current_player())

                            if len(list_of_moves_3) == 0:
                                all_lists.append(move_1_2)
                                continue

                            for move3 in list_of_moves_3:
                                move_1_2_3 = copy.deepcopy(move_1_2)
                                move_1_2_3.append(move3[1])

                                new_chekers3 = new_chekers2.make_move(move3)
                                list_of_moves_4 = new_chekers3.get_possible_jump_for_position(
                                    move3[1][0], move3[1][1], self.get_current_player())

                                if len(list_of_moves_4) == 0:
                                    all_lists.append(move_1_2_3)
                                    continue

                                for move4 in list_of_moves_4:
                                    move_1_2_3_4 = copy.deepcopy(move_1_2_3)
                                    move_1_2_3_4.append(move4[1])

                                    all_lists.append(move_1_2_3_4)

                    if len(all_lists) > 0:
                        for list_moves in all_lists:
                            list_jump_moves.append(list_moves)

        return list_jump_moves


    def get_possible_jump_for_position(self, x, y, pl):

        opponent_player = 'a' if pl == 'r' else 'r'
        delta = [[-1, -1], [-1, 1], [1, -1], [1, 1]] if pl == 'a' else [[1, -1], [1, 1],
                                                                        [-1, -1], [-1, 1]]

        list_moves = []

        if self.board[x][y].lower() == pl:

            for index in range(4):

                if self.board[x][y].islower() and index > 1:
                    continue

                new_x = x + delta[index][0]
                new_y = y + delta[index][1]

                if 0 <= new_x < len(self.board) and 0 <= new_y < len(self.board[x]):

                    if self.board[new_x][new_y].lower() == opponent_player:
                        new_x = new_x + delta[index][0]
                        new_y = new_y + delta[index][1]

                        if 0 <= new_x < len(self.board) and 0 <= new_y < len(
                                self.board[x]) and self.board[new_x][new_y] == ' ':
                            new_move = [[x, y], [new_x, new_y]]
                            list_moves.append(new_move)

        return list_moves

    def get_current_player(self):
        return self.current_player
