from PIL import Image
import os
SRC = r"E:\UE\FarmSim25D\Content\Farm\Art\Source\vectoraith_tileset_farmingsims_terrain_spring_expanded_32x32.png"
OUT = r"E:\UE\FarmSim25D\Content\Farm\Art\Tiles"
im = Image.open(SRC).convert("RGBA")
TILE=32; SCALE=4
def crop(tx,ty,tw=1,th=1):
    return im.crop((tx*TILE, ty*TILE, (tx+tw)*TILE, (ty+th)*TILE))
def save(name, tile):
    up = tile.resize((tile.width*SCALE, tile.height*SCALE), Image.NEAREST)
    path = os.path.join(OUT, name+".png")
    up.save(path)
    print("wrote", name, up.size, os.path.getsize(path))
# Clean deep water fills (most blue, full opaque)
save("T_Water", crop(1, 12, 1, 1))
save("T_WaterDeep", crop(4, 12, 1, 1))
# 2x2 for less obvious seam
save("T_Water2x2", crop(1, 12, 2, 2))
print("done slice")