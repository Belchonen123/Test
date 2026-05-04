"""Pi World - a tiny terminal explorer where the digits of pi paint an infinite map.

Run:
    pip install mpmath colorama
    python pi_world.py

Controls: wasd move, WASD sprint, c conjure, q quit, r restart on death.
"""

import json
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
START_MANA = 3
MAX_MANA = 5
SCORE_FILE = os.path.expanduser('~/.pi_world_score')


def load_high_score():
    try:
        with open(SCORE_FILE) as f:
            return int(json.load(f).get('high_score', 0))
    except (OSError, ValueError, json.JSONDecodeError):
        return 0


def save_high_score(score):
    try:
        with open(SCORE_FILE, 'w') as f:
            json.dump({'high_score': int(score)}, f)
    except OSError:
        pass

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


def mana_bar(mana):
    shown = max(0, min(MAX_MANA, mana))
    full = Fore.LIGHTBLUE_EX + Style.BRIGHT + '*' + Style.RESET_ALL
    empty = Fore.LIGHTBLACK_EX + '-' + Style.RESET_ALL
    return ''.join(full if i < shown else empty for i in range(MAX_MANA))


def effective_tile(state, x, y):
    t = tile_at(x, y)
    if t == WATER and (x, y) in state['conjured']:
        return GRASS
    return t


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def getch():
    """Returns the raw single-character keypress, case preserved."""
    try:
        import msvcrt
        return msvcrt.getch().decode('utf-8', errors='ignore')
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
        return ch


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
    best_str = Fore.LIGHTBLACK_EX + 'best ' + str(state['best']) + Style.RESET_ALL
    boss_str = Style.BRIGHT + Fore.LIGHTMAGENTA_EX + str(state['bosses']) + Style.RESET_ALL
    extras = ''
    if state['combo'] >= 2:
        extras += '   ' + Fore.LIGHTYELLOW_EX + Style.BRIGHT + 'combo x{}'.format(state['combo']) + Style.RESET_ALL
    if is_crit_tile(px, py):
        extras += '   ' + Fore.LIGHTYELLOW_EX + Style.BRIGHT + 'CRIT READY' + Style.RESET_ALL
    print('{}   pos ({:>4},{:>4})   score {} ({})   bosses {}   steps {}{}'.format(
        title, px, py, score_str, best_str, boss_str, state['steps'], extras))
    hint = Fore.LIGHTBLACK_EX + 'wasd  WASD sprint  c conjure  q quit' + Style.RESET_ALL
    print('HP [{}]  MP [{}]   {}'.format(hp_bar(state['hp']), mana_bar(state['mana']), hint))
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
                line += player_glyph(effective_tile(state, wx, wy))
            elif (wx, wy) not in seen:
                line += render_unknown()
            else:
                t = effective_tile(state, wx, wy)
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


def fresh_state(best):
    state = {
        'px': 0, 'py': 0,
        'score': 0, 'hp': START_HP, 'mana': START_MANA, 'steps': 0, 'bosses': 0, 'combo': 0,
        'best': best,
        'seen': set(), 'collected': set(), 'defeated': set(),
        'used_fountains': set(), 'conjured': set(),
        'enemy_hp': {},
        'log': ['Welcome! Stand on a 7-digit tile for CRIT, then walk into a foe to fight.'],
    }
    update_seen(state['seen'], 0, 0)
    return state


ENEMY_MAX_HP = 2
BOSS_MAX_HP = 3
ENEMY_COUNTER = 1
BOSS_COUNTER = 2
CRIT_DIGIT = '7'


def is_crit_tile(x, y):
    return PI_DIGITS[_pi_index(x, y)] == CRIT_DIGIT


def attack_damage(state):
    crit = is_crit_tile(state['px'], state['py'])
    return (2, True) if crit else (1, False)


def resolve_combat(state, kind, ex, ey):
    """Process one attack. Returns True if the enemy was defeated this hit."""
    max_hp = BOSS_MAX_HP if kind == 'boss' else ENEMY_MAX_HP
    counter = BOSS_COUNTER if kind == 'boss' else ENEMY_COUNTER
    cur = state['enemy_hp'].get((ex, ey), max_hp)
    dmg, crit = attack_damage(state)
    cur -= dmg
    crit_label = (Fore.LIGHTYELLOW_EX + Style.BRIGHT + 'CRIT! ' + Style.RESET_ALL) if crit else ''
    if cur <= 0:
        state['defeated'].add((ex, ey))
        state['enemy_hp'].pop((ex, ey), None)
        if kind == 'boss':
            state['score'] += 5
            state['bosses'] += 1
            state['log'].append(crit_label + Fore.LIGHTMAGENTA_EX + Style.BRIGHT
                                + '*** BOSS SLAIN *** +5 score' + Style.RESET_ALL)
        else:
            state['score'] += 1
            state['log'].append(crit_label + Fore.LIGHTRED_EX + Style.BRIGHT
                                + 'Enemy slain! +1 score' + Style.RESET_ALL)
        return True
    state['enemy_hp'][(ex, ey)] = cur
    state['hp'] -= counter
    state['combo'] = 0
    label = 'boss' if kind == 'boss' else 'enemy'
    state['log'].append(crit_label + Fore.LIGHTRED_EX
                        + 'Strike {} ({} HP left). It counters -{} HP.'.format(label, cur, counter)
                        + Style.RESET_ALL)
    return False


def try_move(state, dx, dy):
    """Apply one step of (dx, dy). Returns False if blocked by water."""
    nx, ny = state['px'] + dx, state['py'] + dy
    target = effective_tile(state, nx, ny)
    if target == WATER:
        state['log'].append(Fore.CYAN + 'Splash! Water blocks your path.' + Style.RESET_ALL)
        return False
    kind = enemy_kind(nx, ny)
    if kind and (nx, ny) not in state['defeated']:
        if not resolve_combat(state, kind, nx, ny):
            return False  # enemy survived; player stays on current tile
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
        state['combo'] += 1
        bonus = state['combo']
        state['score'] += bonus
        gained_mana = state['mana'] < MAX_MANA
        state['mana'] = min(MAX_MANA, state['mana'] + 1)
        suffix = ', +1 MP' if gained_mana else ''
        if bonus > 1:
            state['log'].append(Fore.LIGHTYELLOW_EX + Style.BRIGHT
                                + 'Treasure! +{} (combo x{}){}'.format(bonus, state['combo'], suffix)
                                + Style.RESET_ALL)
        else:
            state['log'].append(Fore.LIGHTYELLOW_EX + Style.BRIGHT
                                + 'You found treasure! +1{}'.format(suffix) + Style.RESET_ALL)
    elif target == MOUNTAIN:
        state['log'].append('You scramble up a rocky slope.')
    elif target == FOREST:
        state['log'].append('You push through the trees.')
    return True


def conjure(state):
    """Cast a spell whose effect is determined by the pi digit at the player's tile."""
    if state['mana'] <= 0:
        state['log'].append(Fore.LIGHTBLACK_EX + 'No mana to conjure.' + Style.RESET_ALL)
        return
    state['mana'] -= 1
    px, py = state['px'], state['py']
    d = int(PI_DIGITS[_pi_index(px, py)])

    if d <= 1:
        # Tide: turn nearby water into walkable grass
        count = 0
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                if dx * dx + dy * dy <= 9:
                    wx, wy = px + dx, py + dy
                    if tile_at(wx, wy) == WATER and (wx, wy) not in state['conjured']:
                        state['conjured'].add((wx, wy))
                        count += 1
        state['log'].append(Fore.CYAN + Style.BRIGHT
                            + 'TIDE conjured: {} water tiles parted.'.format(count)
                            + Style.RESET_ALL)
    elif d <= 3:
        # Sight: permanently reveal a wide ring around the player
        for dy in range(-9, 10):
            for dx in range(-9, 10):
                if dx * dx + dy * dy <= 81:
                    state['seen'].add((px + dx, py + dy))
        state['log'].append(Fore.LIGHTCYAN_EX + Style.BRIGHT
                            + 'SIGHT conjured: distant lands revealed.' + Style.RESET_ALL)
    elif d <= 5:
        # Mend: heal HP
        heal = min(START_HP - state['hp'], 3)
        state['hp'] += heal
        state['log'].append(Fore.LIGHTGREEN_EX + Style.BRIGHT
                            + 'MEND conjured: +{} HP.'.format(heal) + Style.RESET_ALL)
    elif d <= 7:
        # Ward: banish nearby foes
        count = 0
        bosses = 0
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                if dx * dx + dy * dy <= 4:
                    wx, wy = px + dx, py + dy
                    kind = enemy_kind(wx, wy)
                    if kind and (wx, wy) not in state['defeated']:
                        state['defeated'].add((wx, wy))
                        state['enemy_hp'].pop((wx, wy), None)
                        count += 1
                        if kind == 'boss':
                            bosses += 1
                            state['bosses'] += 1
                            state['score'] += 5
                        else:
                            state['score'] += 1
        state['log'].append(Fore.LIGHTRED_EX + Style.BRIGHT
                            + 'WARD conjured: {} foes banished ({} boss).'.format(count, bosses)
                            + Style.RESET_ALL)
    else:
        # Hoard: pull score from thin air
        state['score'] += 5
        state['log'].append(Fore.LIGHTYELLOW_EX + Style.BRIGHT
                            + 'HOARD conjured: +5 score from the digits.' + Style.RESET_ALL)


def end_screen(state, message):
    clear_screen()
    print(message)
    new_best = state['score'] > state['best']
    best = max(state['best'], state['score'])
    if new_best:
        save_high_score(best)
        print(Fore.LIGHTYELLOW_EX + Style.BRIGHT
              + 'New best score: {}!'.format(best) + Style.RESET_ALL)
    else:
        print('Final score: {}   (best {})'.format(state['score'], best))
    print('Bosses slain: {}   Steps: {}'.format(state['bosses'], state['steps']))


def run_game(best):
    state = fresh_state(best)
    moves = {'w': (0, -1), 's': (0, 1), 'a': (-1, 0), 'd': (1, 0)}
    while True:
        draw(state)
        if state['hp'] <= 0:
            end_screen(state, Fore.LIGHTRED_EX + Style.BRIGHT
                       + 'You have fallen. Game over.' + Style.RESET_ALL)
            print(Fore.LIGHTBLACK_EX + 'Press r to restart, q to quit.' + Style.RESET_ALL)
            ch = getch().lower()
            return ('restart', state['score']) if ch == 'r' else ('quit', state['score'])
        raw = getch()
        ch = raw.lower()
        if ch == 'q':
            end_screen(state, 'Thanks for exploring Pi World!')
            return 'quit', state['score']
        if ch == 'c':
            conjure(state)
            continue
        if ch not in moves:
            continue
        sprint = raw != ch  # uppercase WASD means sprint two tiles
        dx, dy = moves[ch]
        try_move(state, dx, dy)
        if sprint and state['hp'] > 0:
            try_move(state, dx, dy)


def main():
    best = load_high_score()
    while True:
        outcome, score = run_game(best)
        best = max(best, score)
        if outcome != 'restart':
            return


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        clear_screen()
        print('Bye!')
