#!/usr/bin/env python3
"""Generate the site's favicon PNGs.

No image libraries are available on this machine, so this rasterises the mark
directly: shapes are defined in a 100x100 unit space, sampled 4x4 per output
pixel for anti-aliasing, and written out with a minimal PNG encoder.

The 16px icon uses an optically compensated variant -- heavier strokes and
tighter margins -- because at that size the display geometry's strokes land
near one pixel and wash out under anti-aliasing. Larger sizes use DISPLAY,
which matches static/images/favicon.svg; change one, change both.
"""

import struct
import zlib

BLUE = (0x24, 0x6E, 0xB9)
WHITE = (0xFF, 0xFF, 0xFF)

SS = 4  # supersampling factor per axis


class Geometry:
    """A JH monogram in a 100x100 unit space.

    w      stroke weight
    top    cap line;  bot  baseline
    ro     outer radius of the J hook (its inner radius is ro - w)
    gap    space between the J and the H
    hw     overall H width
    corner plate corner radius
    """

    def __init__(self, w, top, bot, ro, gap, hw, corner):
        self.w, self.top, self.bot, self.corner = w, top, bot, corner
        self.ro, self.ri = ro, ro - w

        total = 2 * ro + gap + hw
        left = (100.0 - total) / 2.0

        # J: hook centre, with the stem rising from it.
        self.jcx = left + ro
        self.jcy = bot - ro
        self.stem = (self.jcx + self.ri, top, self.jcx + ro, self.jcy)

        # H: two stems and a crossbar.
        hx = left + 2 * ro + gap
        mid = (top + bot) / 2.0
        self.h_left = (hx, top, hx + w, bot)
        self.h_right = (hx + hw - w, top, hx + hw, bot)
        self.h_bar = (hx, mid - w / 2.0, hx + hw, mid + w / 2.0)

    def glyphs(self, x, y):
        if _in_rect(x, y, self.stem):
            return True
        if y >= self.jcy:  # lower half of the hook annulus
            d2 = (x - self.jcx) ** 2 + (y - self.jcy) ** 2
            if self.ri**2 <= d2 <= self.ro**2:
                return True
        return (
            _in_rect(x, y, self.h_left)
            or _in_rect(x, y, self.h_right)
            or _in_rect(x, y, self.h_bar)
        )

    def plate(self, x, y, size=100.0):
        r = self.corner
        if not (0 <= x <= size and 0 <= y <= size):
            return False
        cx = min(max(x, r), size - r)
        cy = min(max(y, r), size - r)
        return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


DISPLAY = Geometry(w=9, top=28, bot=71.5, ro=11.5, gap=9, hw=24, corner=22)
COMPACT = Geometry(w=11, top=24, bot=76, ro=12.5, gap=8, hw=26, corner=17)


def _in_rect(x, y, r):
    return r[0] <= x <= r[2] and r[1] <= y <= r[3]


def render(size, geo, bg=BLUE, fg=WHITE, full_bleed=False):
    """Return RGBA rows for a size x size icon.

    full_bleed squares off the corners -- iOS composites apple-touch-icon on
    black and applies its own mask, so transparent corners read as dark notches.
    """
    scale = 100.0 / size
    rows = []
    for py in range(size):
        row = bytearray()
        for px in range(size):
            bg_hits = fg_hits = 0
            for sy in range(SS):
                for sx in range(SS):
                    ux = (px + (sx + 0.5) / SS) * scale
                    uy = (py + (sy + 0.5) / SS) * scale
                    if full_bleed or geo.plate(ux, uy):
                        bg_hits += 1
                        if geo.glyphs(ux, uy):
                            fg_hits += 1
            total = SS * SS
            if bg_hits == 0:
                row += bytes((0, 0, 0, 0))
                continue
            cov_bg = bg_hits / total
            cov_fg = fg_hits / total
            # Composite glyph over plate, then the plate over transparency.
            plate_frac = cov_bg - cov_fg
            r = (bg[0] * plate_frac + fg[0] * cov_fg) / cov_bg
            g = (bg[1] * plate_frac + fg[1] * cov_fg) / cov_bg
            b = (bg[2] * plate_frac + fg[2] * cov_fg) / cov_bg
            row += bytes((round(r), round(g), round(b), round(cov_bg * 255)))
        rows.append(bytes(row))
    return rows


def write_png(path, size, geo, **kw):
    rows = render(size, geo, **kw)
    raw = b"".join(b"\x00" + r for r in rows)  # filter type 0 per scanline

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


if __name__ == "__main__":
    import sys

    out = sys.argv[1].rstrip("/")
    for name, size, geo, bleed in [
        ("favicon-16x16.png", 16, COMPACT, False),
        ("favicon-32x32.png", 32, DISPLAY, False),
        ("apple-touch-icon.png", 180, DISPLAY, True),
        ("android-chrome-192x192.png", 192, DISPLAY, False),
        ("android-chrome-512x512.png", 512, DISPLAY, False),
    ]:
        n = write_png(f"{out}/{name}", size, geo, full_bleed=bleed)
        label = "compact" if geo is COMPACT else "display"
        print(f"{name:32} {size:>4}px  {label}  bleed={str(bleed):5} {n:>7} bytes")
