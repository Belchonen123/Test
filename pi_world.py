"""Pi World - a tiny terminal explorer where the digits of pi paint an infinite map.

Run:
    pip install mpmath colorama
    python pi_world.py

Controls: WASD to move, q to quit.
"""

import os
import sys

from mpmath import mp
from colorama import init as colorama_init, Fore, Back, Style

colorama_init()

# ---- pi digits (>= 100,000) -------------------------------------------------
mp.dps = 100_010
PI_DIGITS = str(mp.pi)[2:]   # drop the leading "3."
PI_LEN = len(PI_DIGITS)

START_DIGIT = 1047

VIEW_W, VIEW_H = 21, 11

WATER, GRASS, FOREST, MOUNTAIN, TREASURE = 'water', 'grass', 'forest', 'mountain', 'treasure'


def tile_at(x, y):
    index = abs(START_DIGIT + x * 37 + y * 91) % PI_LEN
    d = int(PI_DIGITS[index])
    if d <= 2:
        return WATER
    if d <= 4:
        return GRASS
    if d <= 6:
        return FOREST
    if d <= 8:
        return MOUNTAIN
    return TREASURE


def render_tile(t):
    if t == WATER:
        return Back.BLUE + Fore.CYAN + '~' + Style.RESET_ALL
    if t == GRASS:
        return Back.GREEN + Fore.LIGHTGREEN_EX + '.' + Style.RESET_ALL
    if t == FOREST:
        return Back.GREEN + Fore.BLACK + Style.BRIGHT + 'T' + Style.RESET_ALL
    if t == MOUNTAIN:
        return Back.LIGHTBLACK_EX + Fore.WHITE + Style.BRIGHT + '^' + Style.RESET_ALL
    if t == TREASURE:
        return Back.GREEN + Fore.LIGHTYELLOW_EX + Style.BRIGHT + '$' + Style.RESET_ALL
    return ' '


def player_glyph(under):
    bg = {
        WATER: Back.BLUE,
        GRASS: Back.GREEN,
        FOREST: Back.GREEN,
        MOUNTAIN: Back.LIGHTBLACK_EX,
        TREASURE: Back.GREEN,
    }.get(under, Back.BLACK)
    return bg + Fore.LIGHTRED_EX + Style.BRIGHT + '@' + Style.RESET_ALL


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def getch():
    try:
        import msvcrt
        return msvcrt.getch().decode('utf-8', errors='ignore').lower()
    except ImportError:
        import termios
        import tty
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        return ch.lower()


def draw(px, py, score, message, collected):
    clear_screen()
    half_w, half_h = VIEW_W // 2, VIEW_H // 2
    title = Style.BRIGHT + Fore.CYAN + 'Pi World' + Style.RESET_ALL
    score_str = Style.BRIGHT + Fore.LIGHTYELLOW_EX + str(score) + Style.RESET_ALL
    print('{}   pos: ({:>4}, {:>4})   score: {}'.format(title, px, py, score_str))
    print(Fore.LIGHTBLACK_EX + 'WASD to move, q to quit' + Style.RESET_ALL)
    border = '+' + '-' * VIEW_W + '+'
    print(border)
    for vy in range(VIEW_H):
        line = '|'
        for vx in range(VIEW_W):
            wx = px - half_w + vx
            wy = py - half_h + vy
            if wx == px and wy == py:
                line += player_glyph(tile_at(wx, wy))
            else:
                t = tile_at(wx, wy)
                if t == TREASURE and (wx, wy) in collected:
                    line += render_tile(GRASS)
                else:
                    line += render_tile(t)
        line += '|'
        print(line)
    print(border)
    print(message if message else ' ')


def main():
    px, py = 0, 0
    score = 0
    collected = set()
    message = 'Welcome to Pi World! Explore the infinite map of pi.'
    moves = {'w': (0, -1), 's': (0, 1), 'a': (-1, 0), 'd': (1, 0)}
    while True:
        draw(px, py, score, message, collected)
        message = ''
        ch = getch()
        if ch == 'q':
            clear_screen()
            print('Final score: {}'.format(score))
            print('Thanks for exploring Pi World!')
            return
        if ch not in moves:
            continue
        dx, dy = moves[ch]
        nx, ny = px + dx, py + dy
        target = tile_at(nx, ny)
        if target == WATER:
            message = Fore.CYAN + 'Splash! Water blocks your path.' + Style.RESET_ALL
            continue
        px, py = nx, ny
        if target == TREASURE and (px, py) not in collected:
            collected.add((px, py))
            score += 1
            message = Fore.LIGHTYELLOW_EX + Style.BRIGHT + 'You found treasure! +1' + Style.RESET_ALL
        elif target == MOUNTAIN:
            message = 'You scramble up a rocky slope.'
        elif target == FOREST:
            message = 'You push through the trees.'


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        clear_screen()
        print('Bye!')
