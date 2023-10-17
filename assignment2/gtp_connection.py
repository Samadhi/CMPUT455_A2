"""
gtp_connection.py
Module for playing games of Go using GoTextProtocol

Cmput 455 sample code
Written by Cmput 455 TA and Martin Mueller.
Parts of this code were originally based on the gtp module 
in the Deep-Go project by Isaac Henrion and Amos Storkey 
at the University of Edinburgh.
"""
import traceback
import numpy as np
import re
import operator
from sys import stdin, stdout, stderr
from typing import Any, Callable, Dict, List, Tuple
import copy

from board_base import (
    BLACK,
    WHITE,
    EMPTY,
    BORDER,
    GO_COLOR, GO_POINT,
    PASS,
    MAXSIZE,
    coord_to_point,
    opponent,
    where1d # added for undo
)
from board import GoBoard
from board_util import GoBoardUtil
from engine import GoEngine

class GtpConnection:
    def __init__(self, go_engine: GoEngine, board: GoBoard, debug_mode: bool = False) -> None:
        """
        Manage a GTP connection for a Go-playing engine

        Parameters
        ----------
        go_engine:
            a program that can reply to a set of GTP commandsbelow
        board: 
            Represents the current board state.
        """
        self._debug_mode: bool = debug_mode
        self.go_engine = go_engine
        self.board: GoBoard = board
        self.commands: Dict[str, Callable[[List[str]], None]] = {
            "protocol_version": self.protocol_version_cmd,
            "quit": self.quit_cmd,
            "name": self.name_cmd,
            "boardsize": self.boardsize_cmd,
            "showboard": self.showboard_cmd,
            "clear_board": self.clear_board_cmd,
            "komi": self.komi_cmd,
            "version": self.version_cmd,
            "known_command": self.known_command_cmd,
            "genmove": self.genmove_cmd,
            "list_commands": self.list_commands_cmd,
            "play": self.play_cmd,
            "legal_moves": self.legal_moves_cmd,
            "gogui-rules_legal_moves": self.gogui_rules_legal_moves_cmd,
            "gogui-rules_final_result": self.gogui_rules_final_result_cmd,
            "gogui-rules_captured_count": self.gogui_rules_captured_count_cmd,
            "gogui-rules_game_id": self.gogui_rules_game_id_cmd,
            "gogui-rules_board_size": self.gogui_rules_board_size_cmd,
            "gogui-rules_side_to_move": self.gogui_rules_side_to_move_cmd,
            "gogui-rules_board": self.gogui_rules_board_cmd,
            "gogui-analyze_commands": self.gogui_analyze_cmd,
            "timelimit": self.timelimit_cmd,
            "solve": self.solve_cmd
        }

        # argmap is used for argument checking
        # values: (required number of arguments,
        #          error message on argnum failure)
        self.argmap: Dict[str, Tuple[int, str]] = {
            "boardsize": (1, "Usage: boardsize INT"),
            "komi": (1, "Usage: komi FLOAT"),
            "known_command": (1, "Usage: known_command CMD_NAME"),
            "genmove": (1, "Usage: genmove {w,b}"),
            "play": (2, "Usage: play {b,w} MOVE"),
            "legal_moves": (1, "Usage: legal_moves {w,b}"),
        }

    def write(self, data: str) -> None:
        stdout.write(data)

    def flush(self) -> None:
        stdout.flush()

    def start_connection(self) -> None:
        """
        Start a GTP connection. 
        This function continuously monitors standard input for commands.
        """
        line = stdin.readline()
        while line:
            self.get_cmd(line)
            line = stdin.readline()

    def get_cmd(self, command: str) -> None:
        """
        Parse command string and execute it
        """
        if len(command.strip(" \r\t")) == 0:
            return
        if command[0] == "#":
            return
        # Strip leading numbers from regression tests
        if command[0].isdigit():
            command = re.sub("^\d+", "", command).lstrip()

        elements: List[str] = command.split()
        if not elements:
            return
        command_name: str = elements[0]
        args: List[str] = elements[1:]
        if self.has_arg_error(command_name, len(args)):
            return
        if command_name in self.commands:
            try:
                self.commands[command_name](args)
            except Exception as e:
                self.debug_msg("Error executing command {}\n".format(str(e)))
                self.debug_msg("Stack Trace:\n{}\n".format(traceback.format_exc()))
                raise e
        else:
            self.debug_msg("Unknown command: {}\n".format(command_name))
            self.error("Unknown command")
            stdout.flush()

    def has_arg_error(self, cmd: str, argnum: int) -> bool:
        """
        Verify the number of arguments of cmd.
        argnum is the number of parsed arguments
        """
        if cmd in self.argmap and self.argmap[cmd][0] != argnum:
            self.error(self.argmap[cmd][1])
            return True
        return False

    def debug_msg(self, msg: str) -> None:
        """ Write msg to the debug stream """
        if self._debug_mode:
            stderr.write(msg)
            stderr.flush()

    def error(self, error_msg: str) -> None:
        """ Send error msg to stdout """
        stdout.write("? {}\n\n".format(error_msg))
        stdout.flush()

    def respond(self, response: str = "") -> None:
        """ Send response to stdout """
        stdout.write("= {}\n\n".format(response))
        stdout.flush()

    def reset(self, size: int) -> None:
        """
        Reset the board to empty board of given size
        """
        self.board.reset(size)

    def board2d(self) -> str:
        return str(GoBoardUtil.get_twoD_board(self.board))

    def protocol_version_cmd(self, args: List[str]) -> None:
        """ Return the GTP protocol version being used (always 2) """
        self.respond("2")

    def quit_cmd(self, args: List[str]) -> None:
        """ Quit game and exit the GTP interface """
        self.respond()
        exit()

    def name_cmd(self, args: List[str]) -> None:
        """ Return the name of the Go engine """
        self.respond(self.go_engine.name)

    def version_cmd(self, args: List[str]) -> None:
        """ Return the version of the  Go engine """
        self.respond(str(self.go_engine.version))

    def clear_board_cmd(self, args: List[str]) -> None:
        """ clear the board """
        self.reset(self.board.size)
        self.respond()

    def boardsize_cmd(self, args: List[str]) -> None:
        """
        Reset the game with new boardsize args[0]
        """
        self.reset(int(args[0]))
        self.respond()

    def showboard_cmd(self, args: List[str]) -> None:
        self.respond("\n" + self.board2d())

    def showcopy_cmd(self, board) -> None:
        self.respond("\n" + str(GoBoardUtil.get_twoD_board(board)))

    def komi_cmd(self, args: List[str]) -> None:
        """
        Set the engine's komi to args[0]
        """
        self.go_engine.komi = float(args[0])
        self.respond()

    def known_command_cmd(self, args: List[str]) -> None:
        """
        Check if command args[0] is known to the GTP interface
        """
        if args[0] in self.commands:
            self.respond("true")
        else:
            self.respond("false")

    def list_commands_cmd(self, args: List[str]) -> None:
        """ list all supported GTP commands """
        self.respond(" ".join(list(self.commands.keys())))

    def legal_moves_cmd(self, args: List[str]) -> None:
        """
        List legal moves for color args[0] in {'b','w'}
        """
        board_color: str = args[0].lower()
        color: GO_COLOR = color_to_int(board_color)
        moves: List[GO_POINT] = GoBoardUtil.generate_legal_moves(self.board, color)
        gtp_moves: List[str] = []
        for move in moves:
            coords: Tuple[int, int] = point_to_coord(move, self.board.size)
            gtp_moves.append(format_point(coords))
        sorted_moves = " ".join(sorted(gtp_moves))
        self.respond(sorted_moves)

    """
    ==========================================================================
    Assignment 2 - game-specific commands start here
    ==========================================================================
    """
    """
    ==========================================================================
    Assignment 2 - commands we already implemented for you
    ==========================================================================
    """
    def gogui_analyze_cmd(self, args: List[str]) -> None:
        """ We already implemented this function for Assignment 2 """
        self.respond("pstring/Legal Moves For ToPlay/gogui-rules_legal_moves\n"
                     "pstring/Side to Play/gogui-rules_side_to_move\n"
                     "pstring/Final Result/gogui-rules_final_result\n"
                     "pstring/Board Size/gogui-rules_board_size\n"
                     "pstring/Rules GameID/gogui-rules_game_id\n"
                     "pstring/Show Board/gogui-rules_board\n"
                     )

    def gogui_rules_game_id_cmd(self, args: List[str]) -> None:
        """ We already implemented this function for Assignment 2 """
        self.respond("Ninuki")

    def gogui_rules_board_size_cmd(self, args: List[str]) -> None:
        """ We already implemented this function for Assignment 2 """
        self.respond(str(self.board.size))

    def gogui_rules_side_to_move_cmd(self, args: List[str]) -> None:
        """ We already implemented this function for Assignment 2 """
        color = "black" if self.board.current_player == BLACK else "white"
        self.respond(color)

    def gogui_rules_board_cmd(self, args: List[str]) -> None:
        """ We already implemented this function for Assignment 2 """
        size = self.board.size
        str = ''
        for row in range(size-1, -1, -1):
            start = self.board.row_start(row + 1)
            for i in range(size):
                #str += '.'
                point = self.board.board[start + i]
                if point == BLACK:
                    str += 'X'
                elif point == WHITE:
                    str += 'O'
                elif point == EMPTY:
                    str += '.'
                else:
                    assert False
            str += '\n'
        self.respond(str)


    def gogui_rules_final_result_cmd(self, args: List[str]) -> None:
        """ We already implemented this function for Assignment 2 """
        result1 = self.board.detect_five_in_a_row()
        result2 = EMPTY
        if self.board.get_captures(BLACK) >= 10:
            result2 = BLACK
        elif self.board.get_captures(WHITE) >= 10:
            result2 = WHITE

        if (result1 == BLACK) or (result2 == BLACK):
            self.respond("black")
        elif (result1 == WHITE) or (result2 == WHITE):
            self.respond("white")
        elif self.board.get_empty_points().size == 0:
            self.respond("draw")
        else:
            self.respond("unknown")
        return
    
    def game_over(self, board: GoBoard) -> bool:
        #print(board.detect_five_in_a_row())
        result1 = board.detect_five_in_a_row()
        result2 = EMPTY
        if board.get_captures(BLACK) >= 10:
            result2 = BLACK
        elif board.get_captures(WHITE) >= 10:
            result2 = WHITE
        #print("result 1 {} result 2 {}".format(result1, result2))
        #if (result1 != EMPTY) or (result2 != EMPTY) or len(board.moves_played) == 
        if (result1 != EMPTY) or (result2 != EMPTY) or board.get_empty_points().size == 0:
            #print(self.showcopy_cmd(board))
            #print("empty points ", board.get_empty_points().size)
            #print(self.showcopy_cmd(board))
            #print("result is working")
            return True
        return False
    
    def winner(self, board_copy: GoBoard):
        result1 = board_copy.detect_five_in_a_row()
        result2 = EMPTY
        if board_copy.get_captures(BLACK) >= 10:
            result2 = BLACK
        elif board_copy.get_captures(WHITE) >= 10:
            result2 = WHITE
        
        if result1 == BLACK or result2 ==  BLACK:
            return BLACK
        if result1 == WHITE or result2 == WHITE:
            return WHITE
        else:
            return EMPTY

    def gogui_rules_legal_moves_cmd(self, args: List[str]) -> None:
        """ We already implemented this function for Assignment 2 """
        if (self.board.detect_five_in_a_row() != EMPTY) or \
            (self.board.get_captures(BLACK) >= 10) or \
            (self.board.get_captures(WHITE) >= 10):
            self.respond("") 
            return
        legal_moves = self.board.get_empty_points()
        gtp_moves: List[str] = []
        for move in legal_moves:
            coords: Tuple[int, int] = point_to_coord(move, self.board.size)
            gtp_moves.append(format_point(coords))
        sorted_moves = " ".join(sorted(gtp_moves))
        self.respond(sorted_moves)

    def play_cmd(self, args: List[str]) -> None:
        """ We already implemented this function for Assignment 2 """
        try:
            board_color = args[0].lower()
            board_move = args[1]
            if board_color not in ['b', 'w']:
                self.respond('illegal move: "{} {}" wrong color'.format(board_color, board_move))
                return
            coord = move_to_coord(args[1], self.board.size)
            move = coord_to_point(coord[0], coord[1], self.board.size)
            
            color = color_to_int(board_color)
            if not self.board.play_move(move, color):
                # self.respond("Illegal Move: {}".format(board_move))
                self.respond('illegal move: "{} {}" occupied'.format(board_color, board_move))
                return
            else:
                # self.board.try_captures(coord, color)
                self.debug_msg(
                    "Move: {}\nBoard:\n{}\n".format(board_move, self.board2d())
                )
            if len(args) > 2 and args[2] == 'print_move':
                move_as_string = format_point(coord)
                self.respond(move_as_string.lower())
            else:
                self.respond()
        except Exception as e:
            self.respond('illegal move: "{} {}" {}'.format(args[0], args[1], str(e)))

    def gogui_rules_captured_count_cmd(self, args: List[str]) -> None:
        """ We already implemented this function for Assignment 2 """
        self.respond(str(self.board.get_captures(WHITE))+' '+str(self.board.get_captures(BLACK)))

    """
    ==========================================================================
    Assignment 2 - game-specific commands you have to implement or modify
    ==========================================================================
    """

    def genmove_cmd(self, args: List[str]) -> None:
        """ 
        Modify this function for Assignment 2.
        """
        board_color = args[0].lower()
        color = color_to_int(board_color)
        result1 = self.board.detect_five_in_a_row()
        result2 = EMPTY
        if self.board.get_captures(opponent(color)) >= 10:
            result2 = opponent(color)
        if result1 == opponent(color) or result2 == opponent(color):
            self.respond("resign")
            return
        legal_moves = self.board.get_empty_points()
        if legal_moves.size == 0:
            self.respond("pass")
            return
        rng = np.random.default_rng()
        choice = rng.choice(len(legal_moves))
        move = legal_moves[choice]
        move_coord = point_to_coord(move, self.board.size)
        move_as_string = format_point(move_coord)
        self.play_cmd([board_color, move_as_string, 'print_move'])
    
    def timelimit_cmd(self, args: List[str]) -> None:
        """ Implement this function for Assignment 2 """
        pass

    def solve_cmd(self, args: List[str]) -> None:
        """ Implement this function for Assignment 2 """
        # response is winner [move]
        # winner is either b, w, draw, or unknown
        # unknown if solver cannot solve the game within the current time limit
        # If the winner is toPlay or if its a draw, then also write a move that 
        #   you found that achieves this best possible result.
        # If there are several best moves, then write any one of them.
        # If the winner is the opponent or unknown, then do not write any move in your GTP response
        root_board_copy: GoBoard = self.board.copy()
        self.move_dict(root_board_copy)
        #print(self.board.current_player)
        #value = self.run_alphaBeta(root_board_copy, 3, -10000, 10000, self.board.current_player)
        value = self.run_alphaBeta(root_board_copy, 0, -10000, 10000, self.board.current_player)
        print("print end value ", value)
        #print("end value :", value)

        winner = self.winner(root_board_copy)
        moves = root_board_copy.get_empty_points()
        #self.board.ordered_moves_dict = self.staticEvaluation(root_board_copy, self.board.current_player)
        #best_move = value[0]#list(root_board_copy.ordered_moves_dict.keys())[0] # definitly need to change, rn just returning the first key,value pair --> also returning as 11, not e1
        #first_key = list(student_name.keys())[0]
        print(value)
        best_move = point_to_coord(value[1], self.board.size)
        best_move_string = format_point(best_move).lower()


        if self.timelimit_cmd == False: # if timelimit exceeded
            self.respond("unknown")
        elif winner == self.board.current_player or winner == EMPTY: # if current player won or there was a draw. EMPTY means there was a draw
            print("current player in solve is ", self.board.current_player)
            if winner == EMPTY:
                self.respond("draw {}".format(best_move_string)) # 
            elif self.board.current_player == BLACK:
                self.respond("black {}".format(best_move_string)) #
            elif self.board.current_player == WHITE:
                self.respond("white {}".format(best_move_string)) #
        else: # the opponent won so winner != self.board.current_player or EMPTY
            self.respond("white")

    def winner(self, board_copy: GoBoard):
        result1 = board_copy.detect_five_in_a_row()
        result2 = EMPTY
        if board_copy.get_captures(BLACK) >= 10:
            result2 = BLACK
        elif board_copy.get_captures(WHITE) >= 10:
            result2 = WHITE
        
        if result1 == BLACK or result2 ==  BLACK:
            return BLACK
        if result1 == WHITE or result2 == WHITE:
            return WHITE
        else:
            return EMPTY
        
    # use alphabeta algorithm to simulate to find winner
    #def run_alphaBeta(self, board_copy: GoBoard, depth: int, alpha: int, beta: int, current_player: GO_COLOR):
    def run_alphaBeta(self, board_copy: GoBoard, depth: int, alpha: int, beta: int, current_player: GO_COLOR):
        #print("player and inital alpha beta ", current_player, alpha, beta)
        
        undoMoves_dict = board_copy.undoMoves_dict
        #if depth == 0 or self.game_over(board_copy):
        if self.game_over(board_copy):
            print("alphabeta game over")
            #print(self.staticEvaluation(board_copy, current_player))
            #print("current best move is ", board_copy.best_move)
            print("EOF",self.staticEvaluation(board_copy, current_player))
            return self.staticEvaluation(board_copy, current_player)
        
        # use heuristic to order moves
        moves = board_copy.get_empty_points()
        #print("moves to play in loop alphabeta ", moves)
        moves_dict = board_copy.heuristicEvaluation(current_player, moves)
        #moves_to_be_played_dict = board_copy.moves_to_be_played_dict
        

        board_copy.ordered_moves_dict = dict(sorted(moves_dict.items(),key=operator.itemgetter(1), reverse=(True)))

        #print("empty points ", moves)
        #print("empty points with heuristic eval ", moves_dict)
        print("ordered empty points according to heuristic ", board_copy.ordered_moves_dict)
        #print("ordered moves ", board_copy.ordered_moves_dict)
        # print("new board moves played ", new_board.moves_played)
        for move in board_copy.ordered_moves_dict:
            new_board = copy.deepcopy(board_copy)

            if depth == 0:
                print("\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n")

            #for move in moves_dict:
            #rint("ordered empty points according to heuristic in alphabeta lopp ", board_copy.ordered_moves_dict)
            #print("empty points in loop ", moves)
            new_board.simulate_move(move, current_player)

            #print("simulate move {} for player {}:".format(move, board_copy.current_player))
            print(self.showcopy_cmd(board_copy))
            #print("undo moves dict ", undoMoves_dict)
            #value = -self.run_alphaBeta(board_copy, depth-1, -beta, -alpha, board_copy.current_player)
            value = -self.run_alphaBeta(new_board, depth+1, -beta, -alpha, opponent(new_board.current_player))
            print("VALUE",value)
            if depth ==0:
                print("############################ ", value)
            #print("value ", value)
            #print("move and value is ", move, value)
            #print("player and current alpha beta ", current_player, alpha, beta)
        
            if value > alpha:
                #board_copy.best_move = [move, alpha]
                alpha = value
                self.board.best_move = move
                #print("best move in alpha ", board_copy.best_move)
            #     print("hello")
            #     print("value and move in alpha is ", move, value)
            #     print("alphabeta window, alpha, beta ", alpha, beta)
            # print("undo move {} for player {}:".format(move, board_copy.current_player))
            # new_board.undoMove(new_board.current_player) # pass color of current player
            # print("undo!")
            print(self.showcopy_cmd(new_board))
            #print("undo moves dict after undoMove fuct ", undoMoves_dict)
            if value >= beta:                
                # print("value and move in beta is ", move, value)
                # print("alphabeta window, alpha, beta ", alpha, beta)
                print("ret",beta)

                if depth == 0:
                    print("\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n")
                    return beta, move
                # board_copy.best_move = [move, beta]
                #print("best move in beta ", board_copy.best_move)
                return beta
            
       
        #print("returnalpha {} beta {}".format(alpha, beta))
        print("ret",alpha)

        if depth == 0:
            print("\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n")
            return alpha, self.board.best_move
        return alpha

    def staticEvaluation(self, state: GoBoard, current_player: GO_COLOR) -> int:
    #def staticEvaluation(self, state: GoBoard) -> int:
        #empty_points = state.get_empty_points()
        #print("static ")
        #print(self.showcopy_cmd(state))

        win_color = self.winner(state)
        print("win color in static ", win_color)

        #assert win_color != current_player
        #assertion_question = assert (win_color != current_player)
        #print()
        if win_color == current_player and win_color != EMPTY:
            #print("opponent is ", opponent(current_player))
            return -1000
        elif win_color == EMPTY:
            if self.game_over(state): 
                #print("game over")
                return 0
            else: 
                #print("game not over")
                return 1
        else: 
            #print("game won")
            return 10

    def move_dict(self, board_copy: GoBoard):
        undoMoves_dict = board_copy.undoMoves_dict
        moves_to_be_played_dict = board_copy.moves_to_be_played_dict
        
        '''
        undoMoves_dict[where1d(self.board == EMPTY)] = -10 # all empty points
        undoMoves_dict[where1d(self.board == BLACK)] = 1 # all points with stones
        undoMoves_dict[where1d(self.board == WHITE)] = 1

        '''
        # array of empty points
        empty_points_arr = board_copy.get_empty_points()
        # array of points that have white or black stone on them
        stones_arr = board_copy.get_black_and_white_points()

        for empty_points in empty_points_arr: # assign all positions to a empty flag
            undoMoves_dict[empty_points] = [-10]
            moves_to_be_played_dict[empty_points] = None
        for stones in stones_arr: # assign all positoins to a full flag
            undoMoves_dict[stones] = [1]
        
    """
    ==========================================================================
    Assignment 1 - game-specific commands end here
    ==========================================================================
    """

def point_to_coord(point: GO_POINT, boardsize: int) -> Tuple[int, int]:
    """
    Transform point given as board array index 
    to (row, col) coordinate representation.
    Special case: PASS is transformed to (PASS,PASS)
    """
    if point == PASS:
        return (PASS, PASS)
    else:
        NS = boardsize + 1
        return divmod(point, NS)


def format_point(move: Tuple[int, int]) -> str:
    """
    Return move coordinates as a string such as 'A1', or 'PASS'.
    """
    assert MAXSIZE <= 25
    column_letters = "ABCDEFGHJKLMNOPQRSTUVWXYZ"
    if move[0] == PASS:
        return "PASS"
    row, col = move
    if not 0 <= row < MAXSIZE or not 0 <= col < MAXSIZE:
        raise ValueError
    return column_letters[col - 1] + str(row)


def move_to_coord(point_str: str, board_size: int) -> Tuple[int, int]:
    """
    Convert a string point_str representing a point, as specified by GTP,
    to a pair of coordinates (row, col) in range 1 .. board_size.
    Raises ValueError if point_str is invalid
    """
    if not 2 <= board_size <= MAXSIZE:
        raise ValueError("board_size out of range")
    s = point_str.lower()
    if s == "pass":
        return (PASS, PASS)
    try:
        col_c = s[0]
        if (not "a" <= col_c <= "z") or col_c == "i":
            raise ValueError
        col = ord(col_c) - ord("a")
        if col_c < "i":
            col += 1
        row = int(s[1:])
        if row < 1:
            raise ValueError
    except (IndexError, ValueError):
        raise ValueError("wrong coordinate")
    if not (col <= board_size and row <= board_size):
        raise ValueError("wrong coordinate")
    return row, col


def color_to_int(c: str) -> int:
    """convert character to the appropriate integer code"""
    color_to_int = {"b": BLACK, "w": WHITE, "e": EMPTY, "BORDER": BORDER}
    return color_to_int[c]
