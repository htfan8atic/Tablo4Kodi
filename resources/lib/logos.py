# -*- coding: utf-8 -*-
"""Make channel logos uniform: trim padding, fit to a square tile, optionally recolor white.

Pure Python (zlib + struct) so it runs on every Kodi platform without PIL.
Handles 8-bit, non-interlaced PNGs (grey, RGB, palette, grey+alpha, RGBA), which is what
station logos almost always are. Anything else is left as the original image.
"""

import struct
import zlib

# Output tile: 3:2, so it fills both the wide logo boxes skins use in the TV guide and the
# square ones in channel lists without becoming tiny in either.
TILE_W, TILE_H = 300, 200
FILL = 0.84         # logo occupies at most this fraction of the tile (transparent styles)
PLATE_FILL = 0.70   # ... and of the plate when drawn on one
LIGHT_PLATE = (244, 244, 244)
DARK_PLATE = (34, 34, 34)


class Unsupported(Exception):
    pass


# ------------------------------------------------------------------ PNG decode
def _chunks(data):
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise Unsupported("not a PNG")
    pos = 8
    while pos + 8 <= len(data):
        length, ctype = struct.unpack(">I4s", data[pos:pos + 8])
        yield ctype, data[pos + 8:pos + 8 + length]
        pos += 12 + length


def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def decode_png(data):
    """Return (width, height, rgba bytearray)."""
    idat = []
    plte = trns = None
    w = h = depth = ctype = interlace = None
    for t, body in _chunks(data):
        if t == b"IHDR":
            w, h, depth, ctype, _, _, interlace = struct.unpack(">IIBBBBB", body)
        elif t == b"PLTE":
            plte = body
        elif t == b"tRNS":
            trns = body
        elif t == b"IDAT":
            idat.append(body)
        elif t == b"IEND":
            break
    if w is None or depth != 8 or interlace != 0:
        raise Unsupported("only 8-bit non-interlaced PNG")
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(ctype)
    if channels is None:
        raise Unsupported("colour type")
    if w * h > 4000 * 4000:
        raise Unsupported("too large")
    raw = zlib.decompress(b"".join(idat))
    stride = w * channels
    bpp = channels
    out = bytearray(h * stride)
    prev = bytearray(stride)
    pos = 0
    for y in range(h):
        f = raw[pos]
        line = bytearray(raw[pos + 1:pos + 1 + stride])
        pos += 1 + stride
        if f == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 255
        elif f == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif f == 3:
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 255
        elif f == 4:
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                ul = prev[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + _paeth(left, prev[i], ul)) & 255
        out[y * stride:(y + 1) * stride] = line
        prev = line

    rgba = bytearray(w * h * 4)
    n = w * h
    if ctype == 6:
        rgba[:] = out
    elif ctype == 2:
        tkey = struct.unpack(">HHH", trns) if trns and len(trns) == 6 else None
        rgba[0::4], rgba[1::4], rgba[2::4] = out[0::3], out[1::3], out[2::3]
        rgba[3::4] = b"\xff" * n
        if tkey:
            for i in range(n):
                if (out[i * 3], out[i * 3 + 1], out[i * 3 + 2]) == tkey:
                    rgba[i * 4 + 3] = 0
    elif ctype == 0:
        tkey = struct.unpack(">H", trns)[0] if trns and len(trns) == 2 else None
        rgba[0::4] = rgba[1::4] = rgba[2::4] = out
        rgba[3::4] = b"\xff" * n
        if tkey is not None:
            for i in range(n):
                if out[i] == tkey:
                    rgba[i * 4 + 3] = 0
    elif ctype == 4:
        rgba[0::4] = rgba[1::4] = rgba[2::4] = out[0::2]
        rgba[3::4] = out[1::2]
    elif ctype == 3:
        if not plte:
            raise Unsupported("palette missing")
        pal = [(plte[i], plte[i + 1], plte[i + 2], trns[i // 3] if trns and i // 3 < len(trns) else 255)
               for i in range(0, len(plte), 3)]
        for i, idx in enumerate(out):
            r, g, b, a = pal[idx] if idx < len(pal) else (0, 0, 0, 255)
            j = i * 4
            rgba[j], rgba[j + 1], rgba[j + 2], rgba[j + 3] = r, g, b, a
    return w, h, rgba


# ------------------------------------------------------------------ PNG encode
def encode_png(w, h, rgba):
    stride = w * 4
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw += rgba[y * stride:(y + 1) * stride]

    def chunk(t, body):
        return struct.pack(">I", len(body)) + t + body + struct.pack(">I", zlib.crc32(t + body) & 0xffffffff)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))


# ------------------------------------------------------------------ processing
def _make_alpha(w, h, rgba):
    """Logos with no transparency: key out the background colour (taken from the corners)."""
    n = w * h
    if min(rgba[3::4]) < 250:
        return False  # already has real transparency
    corners = [0, w - 1, (h - 1) * w, n - 1]
    bg = [sum(rgba[c * 4 + k] for c in corners) // 4 for k in range(3)]
    for i in range(n):
        j = i * 4
        d = abs(rgba[j] - bg[0]) + abs(rgba[j + 1] - bg[1]) + abs(rgba[j + 2] - bg[2])
        # soft edge: 0 at ~identical, 255 once clearly different
        a = 255 if d >= 96 else (d * 255) // 96
        rgba[j + 3] = a
        if 0 < a < 255:
            # remove the background colour blended into edge pixels (no light/dark fringe)
            for k in range(3):
                v = (rgba[j + k] * 255 - bg[k] * (255 - a)) // a
                rgba[j + k] = 0 if v < 0 else (255 if v > 255 else v)
    return True


def _key_solid_box(w, h, rgba, box):
    """White mode: a logo that is a filled shape (lettering on a coloured badge) would turn
    into a blank white blob. Key out the badge's dominant colour so the lettering remains."""
    x0, y0, x1, y1 = box
    total = opaque = 0
    counts = {}
    for y in range(y0, y1 + 1, 2):
        for x in range(x0, x1 + 1, 2):
            j = (y * w + x) * 4
            total += 1
            if rgba[j + 3] > 200:
                opaque += 1
                k = (rgba[j] >> 4, rgba[j + 1] >> 4, rgba[j + 2] >> 4)
                c = counts.get(k)
                if c is None:
                    c = counts[k] = [0, 0, 0, 0]
                c[0] += 1
                c[1] += rgba[j]
                c[2] += rgba[j + 1]
                c[3] += rgba[j + 2]
    if not total or opaque < total * 0.65 or not counts:
        return False
    n, sr, sg, sb = max(counts.values(), key=lambda c: c[0])
    if n < opaque * 0.4:  # no single badge colour (e.g. a photo); leave it
        return False
    bg = [sr // n, sg // n, sb // n]
    saved = bytes(rgba[3::4])
    for i in range(w * h):
        j = i * 4
        if rgba[j + 3]:
            d = abs(rgba[j] - bg[0]) + abs(rgba[j + 1] - bg[1]) + abs(rgba[j + 2] - bg[2])
            a = 255 if d >= 96 else (d * 255) // 96
            rgba[j + 3] = min(rgba[j + 3], a)
    left = sum(1 for a in rgba[3::4] if a >= 128)
    if left < opaque * 4 * 0.03:  # keying removed (almost) everything: it was just a shape
        rgba[3::4] = saved
        return False
    _drop_rim(w, h, rgba, saved, max(2, int(min(x1 - x0, y1 - y0) * 0.04)))
    return True


def _drop_rim(w, h, rgba, mask, r, thresh=24):
    """Remove what's left of the badge's outline: anything within r pixels of the badge's
    outer edge (measured along rows and columns), so only the lettering inside remains."""
    rim = bytearray(w * h)
    for y in range(h):
        row = mask[y * w:(y + 1) * w]
        xs = [x for x in range(w) if row[x] >= thresh]
        if xs:
            for x in range(xs[0], min(w, xs[0] + r)):
                rim[y * w + x] = 1
            for x in range(max(0, xs[-1] - r + 1), xs[-1] + 1):
                rim[y * w + x] = 1
    for x in range(w):
        col = mask[x::w]
        ys = [y for y in range(h) if col[y] >= thresh]
        if ys:
            for y in range(ys[0], min(h, ys[0] + r)):
                rim[y * w + x] = 1
            for y in range(max(0, ys[-1] - r + 1), ys[-1] + 1):
                rim[y * w + x] = 1
    for i in range(w * h):
        if rim[i]:
            rgba[i * 4 + 3] = 0


def _bbox(w, h, rgba, thresh=24):
    minx, miny, maxx, maxy = w, h, -1, -1
    for y in range(h):
        row = rgba[y * w * 4 + 3:(y + 1) * w * 4:4]
        if max(row) < thresh:
            continue
        miny = min(miny, y)
        maxy = y
        for x, a in enumerate(row):
            if a >= thresh:
                if x < minx:
                    minx = x
                break
        for x in range(w - 1, -1, -1):
            if row[x] >= thresh:
                if x > maxx:
                    maxx = x
                break
    if maxx < 0:
        return 0, 0, w - 1, h - 1
    return minx, miny, maxx, maxy


def _resample(src_w, rgba, x0, y0, cw, ch, dw, dh):
    """Box-filter resize of the crop (x0,y0,cw,ch) to dw x dh, premultiplied alpha."""
    out = bytearray(dw * dh * 4)
    sx, sy = cw / float(dw), ch / float(dh)
    for dy in range(dh):
        ya = y0 + dy * sy
        yb = ya + sy
        iy0, iy1 = int(ya), max(int(ya) + 1, int(yb + 0.999))
        for dx in range(dw):
            xa = x0 + dx * sx
            xb = xa + sx
            ix0, ix1 = int(xa), max(int(xa) + 1, int(xb + 0.999))
            r = g = b = a = cnt = 0
            for yy in range(iy0, min(iy1, y0 + ch)):
                base = (yy * src_w) * 4
                for xx in range(ix0, min(ix1, x0 + cw)):
                    j = base + xx * 4
                    al = rgba[j + 3]
                    r += rgba[j] * al
                    g += rgba[j + 1] * al
                    b += rgba[j + 2] * al
                    a += al
                    cnt += 1
            o = (dy * dw + dx) * 4
            if a:
                out[o], out[o + 1], out[o + 2] = r // a, g // a, b // a
                out[o + 3] = a // cnt
    return out


def _luminance(w, h, rgba):
    """Alpha-weighted average brightness (0-255) of the visible logo pixels."""
    tot = acc = 0
    for i in range(0, w * h * 4, 16):  # every 4th pixel is plenty
        a = rgba[i + 3]
        if a > 32:
            acc += (rgba[i] * 299 + rgba[i + 1] * 587 + rgba[i + 2] * 114) * a
            tot += 1000 * a
    return acc / tot if tot else 0


def _plate(tw, th, color, radius):
    """Anti-aliased rounded rectangle filling the tile."""
    out = bytearray(tw * th * 4)
    r0, g0, b0 = color
    for y in range(th):
        for x in range(tw):
            # distance outside the rounded corner
            cx = radius - x - 0.5 if x < radius else (x + 0.5 - (tw - radius) if x >= tw - radius else 0)
            cy = radius - y - 0.5 if y < radius else (y + 0.5 - (th - radius) if y >= th - radius else 0)
            if cx > 0 and cy > 0:
                d = (cx * cx + cy * cy) ** 0.5 - radius
                a = 0 if d >= 0.5 else (255 if d <= -0.5 else int((0.5 - d) * 255))
            else:
                a = 255
            j = (y * tw + x) * 4
            out[j], out[j + 1], out[j + 2], out[j + 3] = r0, g0, b0, a
    return out


def normalize(data, white=False, plate=False, tile_w=TILE_W, tile_h=TILE_H):
    """PNG bytes in -> PNG bytes out (tile_w x tile_h). Raises Unsupported for images it
    can't handle. plate=True draws the colour logo on a rounded tile whose shade is picked
    for contrast, so it reads on any skin background."""
    w, h, rgba = decode_png(data)
    _make_alpha(w, h, rgba)
    if max(rgba[3::4]) < 24:
        raise Unsupported("nothing left after removing the background")
    x0, y0, x1, y1 = _bbox(w, h, rgba)
    if white and _key_solid_box(w, h, rgba, (x0, y0, x1, y1)):
        x0, y0, x1, y1 = _bbox(w, h, rgba)
    cw, ch = x1 - x0 + 1, y1 - y0 + 1
    fill = PLATE_FILL if plate else FILL
    scale = min(tile_w * fill / float(cw), tile_h * fill / float(ch))
    scale = min(scale, 4.0)  # tiny logos: don't blow them up into mush
    dw, dh = max(1, int(round(cw * scale))), max(1, int(round(ch * scale)))
    if scale < 1.0:
        logo = _resample(w, rgba, x0, y0, cw, ch, dw, dh)
    else:  # nearest-neighbour upscale of the crop
        logo = bytearray(dw * dh * 4)
        for dy in range(dh):
            syy = y0 + min(ch - 1, int(dy / scale))
            for dx in range(dw):
                sxx = x0 + min(cw - 1, int(dx / scale))
                j, o = (syy * w + sxx) * 4, (dy * dw + dx) * 4
                logo[o:o + 4] = rgba[j:j + 4]
    if white:
        logo[0::4] = logo[1::4] = logo[2::4] = b"\xff" * (dw * dh)
    ox, oy = (tile_w - dw) // 2, (tile_h - dh) // 2
    if not plate:
        canvas = bytearray(tile_w * tile_h * 4)
        for y in range(dh):
            d = ((oy + y) * tile_w + ox) * 4
            canvas[d:d + dw * 4] = logo[y * dw * 4:(y + 1) * dw * 4]
        return encode_png(tile_w, tile_h, canvas)
    # mostly-light logos (white lettering) go on a dark plate, everything else on a light one
    color = DARK_PLATE if _luminance(dw, dh, logo) > 175 else LIGHT_PLATE
    canvas = _plate(tile_w, tile_h, color, radius=int(tile_h * 0.14))
    for y in range(dh):
        for x in range(dw):
            s_ = (y * dw + x) * 4
            a = logo[s_ + 3]
            if not a:
                continue
            d = ((oy + y) * tile_w + ox + x) * 4
            for k in range(3):
                canvas[d + k] = (logo[s_ + k] * a + canvas[d + k] * (255 - a)) // 255
    return encode_png(tile_w, tile_h, canvas)
