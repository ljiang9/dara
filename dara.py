#!/usr/bin/env python3
"""Dara（达拉棋）——尼日利亚传统棋类，5x6 棋盘。

规则：
- 棋盘 5 行 x 6 列，双方各 12 子。
- 布子阶段：轮流放子，**不允许放出三连**（含三连以上）。
- 走子阶段：每次把一子正交走一格到空位；若走出恰好三连（不能是四连及以上），
  吃掉对方任意一子。
- 对方只剩 2 子（凑不出三连）或无子可走时获胜。

用法：
    python -m dara            # 人机对战（你是先手）
    python -m dara --auto --games 10 --seed 42   # AI 对 AI 自动演示
"""

import argparse
import copy
import random
import sys

ROWS, COLS = 5, 6
PIECES = 12
P0, P1 = 0, 1
EMPTY = None

DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def other(p):
    return 1 - p


def in_bounds(r, c):
    return 0 <= r < ROWS and 0 <= c < COLS


class Dara:
    """5x6 Dara 对局。"""

    def __init__(self):
        self.board = [[EMPTY] * COLS for _ in range(ROWS)]
        self.placed = [0, 0]      # 布子阶段各方已放子数
        self.phase = "place"      # place / move
        self.turn = P0

    # ---------- 三连检测 ----------

    def _line_len(self, board, r, c, dr, dc, player):
        n = 1
        rr, cc = r + dr, c + dc
        while in_bounds(rr, cc) and board[rr][cc] == player:
            n += 1
            rr += dr
            cc += dc
        rr, cc = r - dr, c - dc
        while in_bounds(rr, cc) and board[rr][cc] == player:
            n += 1
            rr -= dr
            cc -= dc
        return n

    def makes_row(self, board, r, c, player):
        """(r,c) 放上 player 后是否形成 3+ 连珠（任一方向）。"""
        for dr, dc in ((0, 1), (1, 0)):
            if self._line_len(board, r, c, dr, dc, player) >= 3:
                return True
        return False

    def makes_exactly_three(self, board, r, c, player):
        """是否形成恰好三连（吃子条件：三连但不是四连及以上）。"""
        for dr, dc in ((0, 1), (1, 0)):
            if self._line_len(board, r, c, dr, dc, player) == 3:
                return True
        return False

    # ---------- 布子阶段 ----------

    def legal_placements(self, player):
        moves = []
        for r in range(ROWS):
            for c in range(COLS):
                if self.board[r][c] is not EMPTY:
                    continue
                self.board[r][c] = player
                ok = not self.makes_row(self.board, r, c, player)
                self.board[r][c] = EMPTY
                if ok:
                    moves.append((r, c))
        return moves

    def place(self, player, r, c):
        if self.phase != "place":
            raise ValueError("布子阶段已结束")
        if player != self.turn:
            raise ValueError("还没轮到你")
        if not in_bounds(r, c):
            raise ValueError(f"越界: {(r, c)}")
        if self.board[r][c] is not EMPTY:
            raise ValueError(f"格子被占: {(r, c)}")
        self.board[r][c] = player
        if self.makes_row(self.board, r, c, player):
            self.board[r][c] = EMPTY
            raise ValueError("布子不允许形成三连")
        self.placed[player] += 1
        if self.placed[0] >= PIECES and self.placed[1] >= PIECES:
            self.phase = "move"
        self.turn = other(player)

    # ---------- 走子阶段 ----------

    def legal_moves(self, player):
        moves = []
        for r in range(ROWS):
            for c in range(COLS):
                if self.board[r][c] != player:
                    continue
                for dr, dc in DIRS:
                    nr, nc = r + dr, c + dc
                    if in_bounds(nr, nc) and self.board[nr][nc] is EMPTY:
                        moves.append(((r, c), (nr, nc)))
        return moves

    def move(self, player, fr, fc, tr, tc):
        """走一步；若形成恰好三连返回待吃子列表（由调用方选吃哪颗），否则返回 []。"""
        if self.phase != "move":
            raise ValueError("还没进入走子阶段")
        if player != self.turn:
            raise ValueError("还没轮到你")
        if not (in_bounds(fr, fc) and in_bounds(tr, tc)):
            raise ValueError("越界")
        if self.board[fr][fc] != player:
            raise ValueError("起点不是你的子")
        if self.board[tr][tc] is not EMPTY:
            raise ValueError("落点被占")
        if abs(fr - tr) + abs(fc - tc) != 1:
            raise ValueError("只能正交走一格")
        self.board[fr][fc] = EMPTY
        self.board[tr][tc] = player
        capturable = []
        if self.makes_exactly_three(self.board, tr, tc, player):
            foe = other(player)
            capturable = [(r, c) for r in range(ROWS) for c in range(COLS)
                          if self.board[r][c] == foe]
        self.turn = other(player)
        return capturable

    def capture(self, player, r, c):
        """吃掉对方一子（走出三连后的奖励）。"""
        foe = other(player)
        if not in_bounds(r, c):
            raise ValueError("越界")
        if self.board[r][c] != foe:
            raise ValueError("只能吃对方的子")
        self.board[r][c] = EMPTY

    def count(self, player):
        return sum(row.count(player) for row in self.board)

    def winner(self):
        """返回胜者 P0/P1，或 None（未结束）。"""
        if self.phase == "place":
            return None
        for p in (P0, P1):
            foe = other(p)
            if self.count(foe) <= 2:
                return p
            if not self.legal_moves(foe):
                return p
        return None

    def is_over(self):
        return self.winner() is not None

    # ---------- 渲染 ----------

    def render(self):
        sym = {EMPTY: "·", P0: "●", P1: "○"}
        lines = ["   " + " ".join(str(c) for c in range(COLS))]
        for r in range(ROWS):
            lines.append(f"{r}  " + " ".join(sym[self.board[r][c]] for c in range(COLS)))
        return "\n".join(lines)


# ---------- AI ----------

def ai_choose_placement(game, player, rng):
    moves = game.legal_placements(player)
    if not moves:
        return None
    # 贪心：优先占据中心附近，兼顾不给对手送三连机会（布子禁三连，简单取中心）
    def score(m):
        r, c = m
        return -(abs(r - 2) + abs(c - 2.5))
    best = max(score(m) for m in moves)
    cands = [m for m in moves if score(m) == best]
    return rng.choice(cands)


def ai_choose_move(game, player, rng):
    moves = game.legal_moves(player)
    if not moves:
        return None
    foe = other(player)
    scored = []
    for mv in moves:
        (fr, fc), (tr, tc) = mv
        b = copy.deepcopy(game.board)
        b[fr][fc] = EMPTY
        b[tr][tc] = player
        s = 0
        if game.makes_exactly_three(b, tr, tc, player):
            s += 100  # 走出三连吃子
        # 避免送对手三连：检查对手下一步能否在附近成三连（粗略：不走进对手两连的延长线）
        s += rng.random()
        scored.append((s, mv))
    best = max(s for s, _ in scored)
    return rng.choice([mv for s, mv in scored if s == best])


def ai_choose_capture(game, player, capturable, rng):
    # 吃对方子最多的连线威胁子：简单取随机
    return rng.choice(capturable)


# ---------- 对局驱动 ----------

def play_auto(games=10, seed=42, verbose=False):
    rng = random.Random(seed)
    w0 = w1 = draws = 0
    for gi in range(games):
        g = Dara()
        steps = 0
        while not g.is_over() and steps < 600:
            p = g.turn
            if g.phase == "place":
                mv = ai_choose_placement(g, p, rng)
                if mv is None:
                    break
                g.place(p, *mv)
            else:
                mv = ai_choose_move(g, p, rng)
                if mv is None:
                    break
                caps = g.move(p, mv[0][0], mv[0][1], mv[1][0], mv[1][1])
                if caps:
                    cr, cc = ai_choose_capture(g, p, caps, rng)
                    g.capture(p, cr, cc)
            steps += 1
        w = g.winner()
        if w == P0:
            w0 += 1
            res = "甲胜"
        elif w == P1:
            w1 += 1
            res = "乙胜"
        else:
            draws += 1
            res = "和棋"
        if verbose or games <= 10:
            print(f"第 {gi+1}/{games} 局：{res}（{steps} 步，甲 {g.count(P0)} 子/乙 {g.count(P1)} 子）")
    print(f"总计：甲胜 {w0}，乙胜 {w1}，和棋 {draws}")
    return w0, w1, draws


def play_interactive():
    if not sys.stdin.isatty():
        print("交互模式需要终端；无头演示请用 --auto", file=sys.stderr)
        sys.exit(2)
    rng = random.Random()
    g = Dara()
    human = P0
    print("Dara 达拉棋：你是 ●（先手），AI 是 ○。")
    print("布子：输入 行 列（如 2 3）；走子：输入 起行 起列 到行 到列（如 2 3 2 4）；q 退出。")
    while not g.is_over():
        print()
        print(g.render())
        phase = "布子" if g.phase == "place" else "走子"
        print(f"阶段：{phase}，轮到 {'你' if g.turn == human else 'AI'}")
        if g.turn == human:
            try:
                raw = input("> ").strip()
            except EOFError:
                print("\n再见。")
                return
            if raw.lower() == "q":
                return
            try:
                nums = [int(x) for x in raw.split()]
                if g.phase == "place":
                    if len(nums) != 2:
                        raise ValueError("布子请输入：行 列")
                    g.place(human, nums[0], nums[1])
                else:
                    if len(nums) != 4:
                        raise ValueError("走子请输入：起行 起列 到行 到列")
                    caps = g.move(human, *nums)
                    if caps:
                        print("形成三连！选择要吃掉的对方棋子（行 列）：")
                        print(g.render())
                        while True:
                            try:
                                cr, cc = [int(x) for x in input("吃 > ").strip().split()]
                                g.capture(human, cr, cc)
                                break
                            except ValueError as e:
                                print(f"无效：{e}")
            except ValueError as e:
                print(f"无效走法：{e}")
        else:
            p = g.turn
            if g.phase == "place":
                mv = ai_choose_placement(g, p, rng)
                g.place(p, *mv)
                print(f"AI 布子：{mv}")
            else:
                mv = ai_choose_move(g, p, rng)
                if mv is None:
                    print("AI 无棋可走。")
                    break
                caps = g.move(p, mv[0][0], mv[0][1], mv[1][0], mv[1][1])
                print(f"AI 走子：{mv[0]} -> {mv[1]}")
                if caps:
                    cr, cc = ai_choose_capture(g, p, caps, rng)
                    g.capture(p, cr, cc)
                    print(f"AI 吃子：{(cr, cc)}")
    print()
    print(g.render())
    w = g.winner()
    print("你赢了！" if w == human else "AI 赢了。" if w is not None else "和棋。")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Dara 达拉棋（5x6，布子禁三连，走子三连吃子）")
    ap.add_argument("--auto", action="store_true", help="AI 对 AI 自动演示")
    ap.add_argument("--games", type=int, default=10, help="自动演示局数")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--verbose", action="store_true", help="自动演示打印每步")
    args = ap.parse_args(argv)
    if args.auto:
        play_auto(games=args.games, seed=args.seed, verbose=args.verbose)
    else:
        play_interactive()


if __name__ == "__main__":
    main()
