#!/usr/bin/python3
# Set the path to your python3 above

"""
Go0 random Go player
Cmput 455 sample code
Written by Cmput 455 TA and Martin Mueller
"""
from gtp_connection import GtpConnection
from board_base import DEFAULT_SIZE, GO_POINT, GO_COLOR
from board import GoBoard
from board_util import GoBoardUtil
from engine import GoEngine


class Go0(GoEngine):
    def __init__(self) -> None:
        """
        Go player that selects moves randomly from the set of legal moves.
        Does not use the fill-eye filter.
        Passes only if there is no other legal move.
        """
        GoEngine.__init__(self, "Go0", 1.0)

    def get_move(self, board: GoBoard, color: GO_COLOR) -> GO_POINT:
        return GoBoardUtil.generate_random_move(board, color, 
                                                use_eye_filter=False)
    
    def solve(self, board: GoBoard):
        """
        A2: Implement your search algorithm to solve a board
        Change if deemed necessary
        """
        # psuedo code below, is a recursive alpha beta negamax function
        call the alphabeta function to solve
    
    def alphabeta(state, alpha, beta)
        if reached end of game state:
                return staticallyEvaluateForToPlay() --> honestly not completely                    sure what this function does i think it says who won 
        if game is still going:
            do a for loop for all legal moves from current state
                play each legal move
                value = -solve()
                if value > alpha
                    alpha = value
                undo the move
                if value >= beta:
                    return value
        # think we will need function to reset the moves completely in case
        # we run out of time
        return alpha
    
    #need staticallyEvaluateForToPlay() function
    #    assign variable to winner
    #    make sure that winner is current player
    #    if winner is not black or white
    #        if it is the end of the game return 0 --> tie
    #            else return 1 --> we won
    #    else return -10 --> loss

    #need winner function
    #    returns who won

    # need undo all moves functions
    #   calculate the number of undo moves needed would need to track of moves      #       simulated
    #   make sure the number of undos >= 0
    #   do a loop that calls the undo function

    #need undo function
    #    would need to have a list of all the moves played on the board
    #    get the last move put into the board (use pop())
    #    assign the location where we just pop the move to empty
    #    then switch player 

    #need end of game function --> call board.py end of game function

    #need play function --> call board.py play_move but would need to know 
    #    current color

def run() -> None:
    """
    start the gtp connection and wait for commands.
    """
    board: GoBoard = GoBoard(DEFAULT_SIZE)
    con: GtpConnection = GtpConnection(Go0(), board)
    con.start_connection()


if __name__ == "__main__":
    run()
