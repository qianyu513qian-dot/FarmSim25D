from PIL import Image
import os
SRC = r"E:\UE\FarmSim25D\Content\Farm\Art\Source\vectoraith_tileset_farmingsims_terrain_spring_expanded_32x32.png"
OUT = r"E:\UE\FarmSim25D\Content\Farm\Art\Tiles"
PREV = r"E:\UE\FarmSim25D\Content\Farm\Art\Tiles\_preview"
os.makedirs(PREV, exist_ok=True)
im = Image.open(SRC).convert("RGBA")
print("sheet", im.size)
TILE=32
SCALE=4

def crop(tx,ty,tw=1,th=1):
    return im.crop((tx*TILE, ty*TILE, (tx+tw)*TILE, (ty+th)*TILE))

def stats(name, tile):
    # count opaque-ish pixels and avg color
    px = list(tile.getdata())
    opaque = [p for p in px if p[3] > 200]
    if not opaque:
        print(name, "EMPTY/transparent size", tile.size, "bytes_est", len(opaque))
        return
    r = sum(p[0] for p in opaque)/len(opaque)
    g = sum(p[1] for p in opaque)/len(opaque)
    b = sum(p[2] for p in opaque)/len(opaque)
    print(name, "opaque", len(opaque), "/", len(px), "avgRGB=(%.0f,%.0f,%.0f)" % (r,g,b))

# Probe candidate water tiles around pond area rows 8-12 cols 0-5
for ty in range(7, 14):
    for tx in range(0, 8):
        t = crop(tx, ty)
        stats("(%d,%d)" % (tx,ty), t)

# Also search bluish tiles across sheet
print("--- bluish candidates ---")
cands = []
cols = im.size[0]//TILE
rows = im.size[1]//TILE
for ty in range(rows):
    for tx in range(cols):
        t = crop(tx, ty)
        px = [p for p in t.getdata() if p[3] > 200]
        if len(px) < 200:
            continue
        r = sum(p[0] for p in px)/len(px)
        g = sum(p[1] for p in px)/len(px)
        b = sum(p[2] for p in px)/len(px)
        if b > r + 20 and b > g + 10 and b > 80:
            cands.append((b-r, tx, ty, r, g, b, len(px)))
cands.sort(reverse=True)
for c in cands[:25]:
    print("blue score=%.1f tile=(%d,%d) rgb=(%.0f,%.0f,%.0f) n=%d" % (c[0], c[1], c[2], c[3], c[4], c[5], c[6]))

# Save current T_Water for compare
cur = Image.open(os.path.join(OUT, "T_Water.png"))
print("current T_Water", cur.size, cur.mode)
stats("current", cur)