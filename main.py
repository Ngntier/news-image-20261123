#!/usr/bin/env python3
"""news-image-20261123: a dense newspaper front page summing up the world's
news of Monday 23 November 2026.

Pure standard-library Python 3.13. Draws a 1024x1024 PNG with a hand-built
5x7 bitmap font and a minimal zlib PNG encoder. No network, no randomness,
no wall-clock reads: two runs write byte-identical output.

Layout: masthead with the date, two lead stories (Nvidia reinstates Huang;
Ukraine sinks a Russian corvette off Libya), a markets strip, an 18-story
three-column grid, a UTC timeline, and a date-check footer.
"""

import os
import struct
import zlib

W = 1024
H = 1024

PAPER = (247, 242, 231)
INK = (17, 17, 17)
RED = (178, 32, 44)
BLUE = (31, 58, 95)
GREY = (96, 92, 84)
LIGHT = (228, 221, 205)
GOLD = (146, 108, 20)

# ---------------------------------------------------------------- font
# 5x7 bitmap font, uppercase only (text is upper-cased before drawing).
# Each glyph is 7 rows of 5 characters; '#' is ink, '.' is blank.
FONT = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#..##", "#.#.#", "##..#", "#...#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", "..#..", "..#..", "..#.."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    ";": (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "'": ("..#..", "..#..", "..#..", ".....", ".....", ".....", "....."),
    '"': (".#.#.", ".#.#.", ".#.#.", ".....", ".....", ".....", "....."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "(": ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ")": (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    "%": ("#...#", "#..#.", "...#.", "..#..", ".#...", "#..##", "#..##"),
    "&": (".###.", "#...#", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"),
    "+": (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    "=": (".....", ".....", "#####", ".....", "#####", ".....", "....."),
    "$": ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    "#": (".#.#.", ".#.#.", "#####", ".#.#.", "#####", ".#.#.", ".#.#."),
    "*": (".....", "#.#.#", ".###.", "#####", ".###.", "#.#.#", "....."),
    "@": (".###.", "#...#", "#.###", "#.#.#", "#.###", "#....", ".###."),
    "_": (".....", ".....", ".....", ".....", ".....", ".....", "#####"),
    "<": ("...#.", "..#..", ".#...", "#....", ".#...", "..#..", "...#."),
    ">": (".#...", "..#..", "...#.", "....#", "...#.", "..#..", ".#..."),
    "|": ("..#..", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
}


def glyph(ch):
    return FONT.get(ch, FONT["?"])


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self):
        self.buf = bytearray(PAPER[0] for _ in range(W * H * 3))
        for i in range(W * H):
            self.buf[3 * i] = PAPER[0]
            self.buf[3 * i + 1] = PAPER[1]
            self.buf[3 * i + 2] = PAPER[2]

    def px(self, x, y, c):
        if 0 <= x < W and 0 <= y < H:
            i = 3 * (y * W + x)
            self.buf[i] = c[0]
            self.buf[i + 1] = c[1]
            self.buf[i + 2] = c[2]

    def rect(self, x, y, w, h, c):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.px(xx, yy, c)

    def hline(self, x, y, w, c, t=1):
        self.rect(x, y, w, t, c)

    def vline(self, x, y, h, c, t=1):
        self.rect(x, y, t, h, c)

    def border(self, x, y, w, h, c, t=1):
        self.hline(x, y, w, c, t)
        self.hline(x, y + h - t, w, c, t)
        self.vline(x, y, h, c, t)
        self.vline(x + w - t, y, h, c, t)

    def line(self, x0, y0, x1, y1, c, t=1):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            for a in range(t):
                for b in range(t):
                    self.px(x + a, y + b, c)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def disc(self, cx, cy, r, c):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy <= r * r:
                    self.px(cx + dx, cy + dy, c)


def text_w(s, scale):
    return len(s) * 6 * scale - scale


def draw_text(cv, x, y, s, scale, c):
    s = s.upper()
    cx = x
    for ch in s:
        g = glyph(ch)
        for row in range(7):
            bits = g[row]
            for col in range(5):
                if bits[col] == "#":
                    cv.rect(cx + col * scale, y + row * scale, scale, scale, c)
        cx += 6 * scale
    return cx


def draw_text_centered(cv, y, s, scale, c):
    x = (W - text_w(s, scale)) // 2
    draw_text(cv, x, y, s, scale, c)


def wrap(s, maxw, scale):
    lines = []
    cur = ""
    for word in s.split(" "):
        trial = (cur + " " + word).strip()
        if text_w(trial, scale) <= maxw:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_block(cv, x, y, lines, scale, c, leading):
    for i, ln in enumerate(lines):
        draw_text(cv, x, y + i * leading, ln, scale, c)


# ---------------------------------------------------------------- stories
# (kicker, headline, summary) — every story happened or was first reported
# on Monday 23 November 2026.
LEAD1 = (
    "TECH & MARKETS - REUTERS",
    "HUANG IS BACK AT NVIDIA",
    "Nvidia reinstates co-founder Jensen Huang as chief executive, 11 days "
    "after he resigned. Shares jump about 33% and lift Wall Street after a "
    "week of AI sell-off.",
)
LEAD2 = (
    "WAR AT SEA - AP",
    "UKRAINE SINKS RUSSIAN SHIP OFF LIBYA",
    "Seven drones sink the corvette Merkury; a second ship is hit.",
)

GRID = [
    ("CLIMATE - REUTERS", "COP31 ENDS WITH NO DEAL",
     "Record-long UN talks in Turkey end with no deal."),
    ("POLITICS - AP", "DEMOCRATS TAKE 258 SEATS",
     "Largest House majority since 1992; NC flips."),
    ("EU - AP", "EU PROPOSES 22ND SANCTIONS PACKAGE",
     "Targets 60 banks, crypto and 70 shadow-fleet ships."),
    ("DIPLOMACY - REUTERS", "TRUMP MEETS PUTIN AND XI",
     "Trump calls Putin 'my friend' in Shenzhen."),
    ("NATO - REUTERS", "NATO MEETS ON POLAND STRIKES",
     "Allies meet in Berlin over Poland strikes."),
    ("ASIA - AP", "INDIA AIDS NEPAL WITH 1.4BN EUROS",
     "Modi offers rebuild funds after the August floods."),
    ("DISASTER - AP", "FACTORY FIRE KILLS 24 IN INDONESIA",
     "Sweets factory blaze in West Java; 30 missing."),
    ("US - AP", "AMTRAK TRAIN DERAILS IN LOUISIANA",
     "Train hits a stuck truck; five hurt, 95 aboard."),
    ("US - AP", "FBI PROBES HACK OF CRIME DATABASE",
     "Bureau probes a breach of the police database."),
    ("US - AP", "TRUMP CURBS CONGRESS SUBPOENAS",
     "Order curbs Congress information requests."),
    ("SPACE - ESA", "BEPICOLOMBO REACHES MERCURY",
     "ESA-JAXA probes reach Mercury after eight years."),
    ("SCIENCE - GUARDIAN", "AI AND THE RIEMANN PROOF",
     "Groups check parts of an AI proof; maths split."),
    ("HEALTH - NHS", "NHS TRIALS AI IN BREAST SCREENING",
     "Trial tests whether AI can spot cancer earlier."),
    ("ECONOMY - EUROSTAT", "EURO INFLATION HITS 4.0%",
     "Prices rise faster across the euro area, data shows."),
    ("TECH - REUTERS", "ORACLE: OPENAI BUILD IS FUNDED",
     "Oracle says its $300bn OpenAI deal is funded."),
    ("SPORT - ESPN", "SKUBAL'S $450M METS DEAL",
     "Two-time Cy Young winner signs record pitcher deal."),
    ("SPORT - ESPN", "49ERS ROUT VIKINGS IN MEXICO CITY",
     "San Francisco win 35-10; Purdy throws three TDs."),
    ("SPORT - ESPN", "GIANTS STUN JAGUARS 23-18",
     "Giants upset Jacksonville for a shock win."),
]

# (UTC time, short label) — the day as it unfolded.
TIMELINE = [
    ("00:39", "EBOLA RESPONSE HIT BY FIGHTING"),
    ("03:15", "BELGIUM AIRPORTS SHUT IN STRIKE"),
    ("03:27", "MANCHESTER ARENA EVACUATED"),
    ("04:00", "GAZA 99% CONTAMINATED: OXFAM"),
    ("05:00", "NINE SHOT AT CALIFORNIA CONCERT"),
    ("06:45", "KIM REBUFFS TRUMP TALKS OFFER"),
    ("07:36", "LION LOOSE OUTSIDE ISTANBUL"),
    ("11:15", "TINUBU: VILLA HIT BY POWER CUTS"),
]

MARKETS = ("MARKETS: S&P 500 7,243 +4.82% | NIKKEI -5% | "
           "FTSE 10,481 +1.30% | BRENT $86.78")


# ---------------------------------------------------------------- drawing
def draw_ship(cv, x, y, s, c):
    """Small warship silhouette: hull, bridge, mast, waves."""
    cv.rect(x, y + 10 * s, 44 * s, 5 * s, c)          # hull
    cv.rect(x + 4 * s, y + 15 * s, 36 * s, 2 * s, c)  # keel line
    cv.rect(x + 12 * s, y + 4 * s, 12 * s, 6 * s, c)  # bridge
    cv.rect(x + 26 * s, y + 6 * s, 6 * s, 4 * s, c)   # funnel
    cv.vline(x + 17 * s, y, 4 * s, c, 1)              # mast
    cv.rect(x + 17 * s, y, 6 * s, 1, c)               # flag
    for k in range(4):                                # waves
        cv.hline(x - 4 * s + k * 14 * s, y + 19 * s, 9 * s, c, 1)
    # two drones above
    cv.disc(x + 6 * s, y - 6 * s, 2, c)
    cv.disc(x + 34 * s, y - 9 * s, 2, c)


def draw_chart(cv, x, y, w, h, c):
    """Rising market line with an arrowhead."""
    pts = [(0, h - 8), (w // 5, h - 14), (2 * w // 5, h - 6),
           (3 * w // 5, h - 22), (4 * w // 5, h - 30), (w - 6, 4)]
    for a, b in zip(pts, pts[1:]):
        cv.line(x + a[0], y + a[1], x + b[0], y + b[1], c, 2)
    cv.line(x + w - 6, y + 4, x + w - 14, y + 2, c, 2)
    cv.line(x + w - 6, y + 4, x + w - 8, y + 12, c, 2)
    cv.hline(x, y + h - 2, w, GREY, 1)


def render():
    cv = Canvas()
    mx = 16  # margin

    # ---- masthead ----
    draw_text_centered(cv, 10, "THE WORLD TODAY", 6, INK)
    draw_text(cv, mx, 66, "VOL. I - NO. 23", 2, GREY)
    right = "ONE DAY, ONE PAGE"
    draw_text(cv, W - mx - text_w(right, 2), 66, right, 2, GREY)
    draw_text_centered(cv, 62, "MONDAY 23 NOVEMBER 2026", 3, RED)
    cv.hline(mx, 56, W - 2 * mx, INK, 2)
    cv.hline(mx, 90, W - 2 * mx, INK, 2)

    # ---- lead row ----
    ly = 100
    cv.vline(648, ly, 136, INK, 1)
    # lead 1: Nvidia
    draw_text(cv, mx, ly + 4, LEAD1[0], 2, RED)
    draw_text(cv, mx, ly + 26, LEAD1[1], 3, INK)
    lines = wrap(LEAD1[2], 500, 2)
    draw_block(cv, mx, ly + 58, lines[:4], 2, INK, 15)
    draw_chart(cv, 540, ly + 92, 96, 40, BLUE)
    draw_text(cv, 540, ly + 76, "+33%", 2, BLUE)
    # lead 2: Ukraine sinks ship
    draw_text(cv, 664, ly + 4, LEAD2[0], 2, RED)
    hl = wrap(LEAD2[1], 226, 2)
    draw_block(cv, 664, ly + 26, hl, 2, INK, 18)
    draw_ship(cv, 906, ly + 26, 1, BLUE)
    lines = wrap(LEAD2[2], 328, 2)
    draw_block(cv, 664, ly + 86, lines[:3], 2, INK, 15)

    cv.hline(mx, 242, W - 2 * mx, INK, 2)

    # ---- markets strip ----
    draw_text_centered(cv, 250, MARKETS, 2, INK)
    cv.hline(mx, 270, W - 2 * mx, INK, 1)

    # ---- grid header ----
    draw_text(cv, mx, 278, "THE DAY'S NEWS - 18 STORIES", 2, INK)
    right = "ALL TIMES UTC"
    draw_text(cv, W - mx - text_w(right, 2), 278, right, 2, GREY)
    cv.hline(mx, 296, W - 2 * mx, INK, 2)

    # ---- story grid: 3 columns x 6 rows ----
    col_x = [16, 352, 688]
    col_w = 320
    gy = 304
    row_h = 95
    for idx, (kicker, headline, summary) in enumerate(GRID):
        col = idx % 3
        row = idx // 3
        x = col_x[col]
        y = gy + row * row_h
        draw_text(cv, x, y, kicker, 2, RED)
        hl = wrap(headline, col_w, 2)
        draw_block(cv, x, y + 18, hl[:2], 2, INK, 17)
        sl = wrap(summary, col_w, 2)
        draw_block(cv, x, y + 56, sl[:2], 2, INK, 15)
    for r in range(1, 6):
        cv.hline(mx, gy + r * row_h - 3, W - 2 * mx, LIGHT, 1)
    for cx in (344, 680):
        cv.vline(cx, gy, 6 * row_h - 8, LIGHT, 1)

    # ---- timeline ----
    ty = 882
    draw_text(cv, mx, ty, "THE DAY IN UTC", 2, INK)
    cv.hline(mx, ty + 18, W - 2 * mx, INK, 2)
    for i, (t, label) in enumerate(TIMELINE):
        col = 0 if i < 4 else 1
        row = i % 4
        x = mx if col == 0 else 528
        y = ty + 26 + row * 16
        draw_text(cv, x, y, t, 2, RED)
        draw_text(cv, x + text_w(t + " ", 2), y, label, 2, INK)

    # ---- footer: date check + sources ----
    cv.hline(mx, 978, W - 2 * mx, INK, 2)
    draw_text_centered(cv, 986, "DATE CHECK: MONDAY 23 NOVEMBER 2026", 2, RED)
    draw_text_centered(
        cv, 1004,
        "SOURCES: REUTERS, AP, DOW JONES, THE GUARDIAN, NATURE, ESA, ESPN, NYT, WHO, OXFAM",
        2, GREY)

    return png_bytes(cv.buf)


def png_bytes(buf):
    def chunk(typ, data):
        out = struct.pack(">I", len(data)) + typ + data
        out += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + bytes(buf[y * W * 3:(y + 1) * W * 3])
                   for y in range(H))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    data = render()
    with open(os.path.join(outdir, "entry.png"), "wb") as f:
        f.write(data)


if __name__ == "__main__":
    main()
