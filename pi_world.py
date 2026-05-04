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
SIGHT_RADIUS = 4
START_HP = 10

WATER, GRASS, FOREST, MOUNTAIN, TREASURE = 'water', 'grass', 'forest', 'mountain', 'treasure'


def _pi_index(x, y):
    return abs(START_DIGIT + x * 37 + y * 91) % PI_LEN


def tile_at(x, y):
    d = int(PI_DIGITS[_pi_index(x, y)])
    if d <= 2:
        return WATER
    if d <= 4:
        return GRASS
    if d <= 6:
        return FOREST
    if d <= 8:
        return MOUNTAIN
    return TREASURE


def enemy_at(x, y):
    """Enemy spawns on walkable land where three pi-digits in a row match."""
    t = tile_at(x, y)
    if t not in (GRASS, FOREST, MOUNTAIN):
        return False
    i = _pi_index(x, y)
    a = PI_DIGITS[i]
    b = PI_DIGITS[(i + 1) % PI_LEN]
    c = PI_DIGITS[(i + 2) % PI_LEN]
    return a == b == c


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


def render_enemy(under):
    bg = {GRASS: Back.GREEN, FOREST: Back.GREEN,
          MOUNTAIN: Back.LIGHTBLACK_EX}.get(under, Back.BLACK)
    return bg + Fore.LIGHTRED_EX + Style.BRIGHT + 'E' + Style.RESET_ALL


def render_unknown():
    return Back.BLACK + Fore.LIGHTBLACK_EX + ' ' + Style.RESET_ALL


def player_glyph(under):
    bg = {
        WATER: Back.BLUE,
        GRASS: Back.GREEN,
        FOREST: Back.GREEN,
        MOUNTAIN: Back.LIGHTBLACK_EX,
        TREASURE: Back.GREEN,
    }.get(under, Back.BLACK)
    return bg + Fore.LIGHTRED_EX + Style.BRIGHT + '@' + Style.RESET_ALL


def hp_bar(hp):
    full = Fore.LIGHTRED_EX + Style.BRIGHT + '#' + Style.RESET_ALL
    empty = Fore.LIGHTBLACK_EX + '-' + Style.RESET_ALL
    return ''.join(full if i < hp else empty for i in range(START_HP))


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


def update_seen(seen, px, py):
    r = SIGHT_RADIUS
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r:
                seen.add((px + dx, py + dy))


def draw(px, py, score, hp, steps, log, seen, collected, defeated):
    clear_screen()
    half_w, half_h = VIEW_W // 2, VIEW_H // 2
    title = Style.BRIGHT + Fore.CYAN + 'Pi World' + Style.RESET_ALL
    score_str = Style.BRIGHT + Fore.LIGHTYELLOW_EX + str(score) + Style.RESET_ALL
    print('{}   pos ({:>4},{:>4})   score {}   steps {}'.format(
        title, px, py, score_str, steps))
    hint = Fore.LIGHTBLACK_EX + 'WASD to move, q to quit' + Style.RESET_ALL
    print('HP [{}]   {}'.format(hp_bar(hp), hint))
    border = '+' + '-' * VIEW_W + '+'
    print(border)
    for vy in range(VIEW_H):
        line = '|'
        for vx in range(VIEW_W):
            wx = px - half_w + vx
            wy = py - half_h + vy
            if wx == px and wy == py:
                line += player_glyph(tile_at(wx, wy))
            elif (wx, wy) not in seen:
                line += render_unknown()
            else:
                t = tile_at(wx, wy)
                if t == TREASURE and (wx, wy) in collected:
                    line += render_tile(GRASS)
                elif enemy_at(wx, wy) and (wx, wy) not in defeated:
                    line += render_enemy(t)
                else:
                    line += render_tile(t)
        line += '|'
        print(line)
    print(border)
    recent = log[-3:]
    while len(recent) < 3:
        recent = [''] + recent
    for entry in recent:
        print(entry if entry else ' ')


def main():
    px, py = 0, 0
    score = 0
    hp = START_HP
    steps = 0
    seen = set()
    collected = set()
    defeated = set()
    log = ['Welcome to Pi World! Collect $, fight E, avoid ~.']
    update_seen(seen, px, py)
    moves = {'w': (0, -1), 's': (0, 1), 'a': (-1, 0), 'd': (1, 0)}
    while True:
        draw(px, py, score, hp, steps, log, seen, collected, defeated)
        if hp <= 0:
            print(Fore.LIGHTRED_EX + Style.BRIGHT + 'You have fallen. Game over.' + Style.RESET_ALL)
            print('Final score: {}   Steps: {}'.format(score, steps))
            return
        ch = getch()
        if ch == 'q':
            clear_screen()
            print('Final score: {}   Steps: {}'.format(score, steps))
            print('Thanks for exploring Pi World!')
            return
        if ch not in moves:
            continue
        dx, dy = moves[ch]
        nx, ny = px + dx, py + dy
        target = tile_at(nx, ny)
        if target == WATER:
            log.append(Fore.CYAN + 'Splash! Water blocks your path.' + Style.RESET_ALL)
            continue
        if enemy_at(nx, ny) and (nx, ny) not in defeated:
            hp -= 1
            defeated.add((nx, ny))
            log.append(Fore.LIGHTRED_EX + Style.BRIGHT
                       + 'You defeat an enemy! -1 HP' + Style.RESET_ALL)
        px, py = nx, ny
        steps += 1
        update_seen(seen, px, py)
        if target == TREASURE and (px, py) not in collected:
            collected.add((px, py))
            score += 1
            log.append(Fore.LIGHTYELLOW_EX + Style.BRIGHT
                       + 'You found treasure! +1' + Style.RESET_ALL)
        elif target == MOUNTAIN:
            log.append('You scramble up a rocky slope.')
        elif target == FOREST:
            log.append('You push through the trees.')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        clear_screen()
        print('Bye!')
