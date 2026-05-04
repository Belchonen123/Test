"""Pi World - a tiny terminal explorer where the digits of pi paint an infinite map.

Run:
    pip install mpmath colorama
    python pi_world.py

Controls: WASD to move, q to quit. After death, press r to restart.
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


def enemy_kind(x, y):
    """None / 'enemy' (3 matching digits) / 'boss' (4 matching digits)."""
    t = tile_at(x, y)
    if t not in (GRASS, FOREST, MOUNTAIN):
        return None
    i = _pi_index(x, y)
    a = PI_DIGITS[i]
    b = PI_DIGITS[(i + 1) % PI_LEN]
    c = PI_DIGITS[(i + 2) % PI_LEN]
    if not (a == b == c):
        return None
    return 'boss' if PI_DIGITS[(i + 3) % PI_LEN] == a else 'enemy'


def healing_at(x, y):
    """Healing fountain on grass/forest where pi has 3 strictly ascending digits."""
    t = tile_at(x, y)
    if t not in (GRASS, FOREST):
        return False
    i = _pi_index(x, y)
    a = int(PI_DIGITS[i])
    b = int(PI_DIGITS[(i + 1) % PI_LEN])
    c = int(PI_DIGITS[(i + 2) % PI_LEN])
    return b == a + 1 and c == b + 1


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


def _bg_for(t):
    return {
        WATER: Back.BLUE,
        GRASS: Back.GREEN,
        FOREST: Back.GREEN,
        MOUNTAIN: Back.LIGHTBLACK_EX,
        TREASURE: Back.GREEN,
    }.get(t, Back.BLACK)


def render_enemy(under):
    return _bg_for(under) + Fore.LIGHTRED_EX + Style.BRIGHT + 'E' + Style.RESET_ALL


def render_boss(under):
    return _bg_for(under) + Fore.LIGHTMAGENTA_EX + Style.BRIGHT + 'B' + Style.RESET_ALL


def render_fountain(under):
    return _bg_for(under) + Fore.LIGHTCYAN_EX + Style.BRIGHT + '+' + Style.RESET_ALL


def render_unknown():
    return Back.BLACK + Fore.LIGHTBLACK_EX + ' ' + Style.RESET_ALL


def player_glyph(under):
    return _bg_for(under) + Fore.LIGHTRED_EX + Style.BRIGHT + '@' + Style.RESET_ALL


def hp_bar(hp):
    shown = max(0, min(START_HP, hp))
    full = Fore.LIGHTRED_EX + Style.BRIGHT + '#' + Style.RESET_ALL
    empty = Fore.LIGHTBLACK_EX + '-' + Style.RESET_ALL
    return ''.join(full if i < shown else empty for i in range(START_HP))


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


def draw(state):
    clear_screen()
    px, py = state['px'], state['py']
    half_w, half_h = VIEW_W // 2, VIEW_H // 2
    title = Style.BRIGHT + Fore.CYAN + 'Pi World' + Style.RESET_ALL
    score_str = Style.BRIGHT + Fore.LIGHTYELLOW_EX + str(state['score']) + Style.RESET_ALL
    boss_str = Style.BRIGHT + Fore.LIGHTMAGENTA_EX + str(state['bosses']) + Style.RESET_ALL
    print('{}   pos ({:>4},{:>4})   score {}   bosses {}   steps {}'.format(
        title, px, py, score_str, boss_str, state['steps']))
    hint = Fore.LIGHTBLACK_EX + 'WASD move, q quit' + Style.RESET_ALL
    print('HP [{}]   {}'.format(hp_bar(state['hp']), hint))
    border = '+' + '-' * VIEW_W + '+'
    print(border)
    seen = state['seen']
    collected = state['collected']
    defeated = state['defeated']
    used_fountains = state['used_fountains']
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
                elif healing_at(wx, wy) and (wx, wy) not in used_fountains:
                    line += render_fountain(t)
                else:
                    kind = enemy_kind(wx, wy)
                    if kind and (wx, wy) not in defeated:
                        line += render_boss(t) if kind == 'boss' else render_enemy(t)
                    else:
                        line += render_tile(t)
        line += '|'
        print(line)
    print(border)
    recent = state['log'][-3:]
    while len(recent) < 3:
        recent = [''] + recent
    for entry in recent:
        print(entry if entry else ' ')


def fresh_state():
    state = {
        'px': 0, 'py': 0,
        'score': 0, 'hp': START_HP, 'steps': 0, 'bosses': 0,
        'seen': set(), 'collected': set(), 'defeated': set(), 'used_fountains': set(),
        'log': ['Welcome to Pi World! $ treasure  E enemy  B boss  + fountain'],
    }
    update_seen(state['seen'], 0, 0)
    return state


def run_game():
    state = fresh_state()
    moves = {'w': (0, -1), 's': (0, 1), 'a': (-1, 0), 'd': (1, 0)}
    while True:
        draw(state)
        if state['hp'] <= 0:
            print(Fore.LIGHTRED_EX + Style.BRIGHT + 'You have fallen. Game over.' + Style.RESET_ALL)
            print('Final score: {}   Bosses slain: {}   Steps: {}'.format(
                state['score'], state['bosses'], state['steps']))
            print(Fore.LIGHTBLACK_EX + 'Press r to restart, q to quit.' + Style.RESET_ALL)
            ch = getch()
            return 'restart' if ch == 'r' else 'quit'
        ch = getch()
        if ch == 'q':
            clear_screen()
            print('Final score: {}   Bosses slain: {}   Steps: {}'.format(
                state['score'], state['bosses'], state['steps']))
            print('Thanks for exploring Pi World!')
            return 'quit'
        if ch not in moves:
            continue
        dx, dy = moves[ch]
        nx, ny = state['px'] + dx, state['py'] + dy
        target = tile_at(nx, ny)
        if target == WATER:
            state['log'].append(Fore.CYAN + 'Splash! Water blocks your path.' + Style.RESET_ALL)
            continue
        kind = enemy_kind(nx, ny)
        if kind and (nx, ny) not in state['defeated']:
            state['defeated'].add((nx, ny))
            if kind == 'boss':
                state['hp'] -= 3
                state['score'] += 5
                state['bosses'] += 1
                state['log'].append(Fore.LIGHTMAGENTA_EX + Style.BRIGHT
                                    + '*** BOSS SLAIN *** -3 HP, +5 score' + Style.RESET_ALL)
            else:
                state['hp'] -= 1
                state['log'].append(Fore.LIGHTRED_EX + Style.BRIGHT
                                    + 'You defeat an enemy! -1 HP' + Style.RESET_ALL)
        state['px'], state['py'] = nx, ny
        state['steps'] += 1
        update_seen(state['seen'], nx, ny)
        if (healing_at(nx, ny)
                and (nx, ny) not in state['used_fountains']
                and state['hp'] < START_HP):
            heal = min(START_HP - state['hp'], 3)
            state['hp'] += heal
            state['used_fountains'].add((nx, ny))
            state['log'].append(Fore.LIGHTCYAN_EX + Style.BRIGHT
                                + 'You drink from a fountain! +{} HP'.format(heal)
                                + Style.RESET_ALL)
        if target == TREASURE and (nx, ny) not in state['collected']:
            state['collected'].add((nx, ny))
            state['score'] += 1
            state['log'].append(Fore.LIGHTYELLOW_EX + Style.BRIGHT
                                + 'You found treasure! +1' + Style.RESET_ALL)
        elif target == MOUNTAIN:
            state['log'].append('You scramble up a rocky slope.')
        elif target == FOREST:
            state['log'].append('You push through the trees.')


def main():
    while True:
        outcome = run_game()
        if outcome != 'restart':
            return


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        clear_screen()
        print('Bye!')
