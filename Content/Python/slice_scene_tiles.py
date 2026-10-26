# -*- coding: utf-8 -*-
"""Slice VectoRaith Compact 32x32 tiles -> 4x NEAREST PNGs for FarmSim scene."""
from PIL import Image
import os

SRC = r"E:\UE\FarmSim25D\Content\Farm\Art\Source"
OUT = r"E:\UE\FarmSim25D\Content\Farm\Art\Tiles"
PREV = r"E:\UE\FarmSim25D\Content\Farm\Art\Tiles\_preview"
os.makedirs(OUT, exist_ok=True)
os.makedirs(PREV, exist_ok=True)

TILE = 32
SCALE = 4

SHEETS = {
    "spring": os.path.join(SRC, "vectoraith_tileset_farmingsims_terrain_spring_expanded_32x32.png"),
    "buildings": os.path.join(SRC, "vectoraith_tileset_farmingsims_buildings_32x32.png"),
    "details": os.path.join(SRC, "vectoraith_tileset_farmingsims_details_32x32.png"),
    "orchard": os.path.join(SRC, "vectoraith_tileset_farmingsims_orchard_32x32.png"),
    "crops": os.path.join(SRC, "vectoraith_tileset_farmingsims_crops_32x32.png"),
    "crops_dense": os.path.join(SRC, "vectoraith_tileset_farmingsims_crops_dense_32x32.png"),
}

def load(name):
    im = Image.open(SHEETS[name]).convert("RGBA")
    assert im.size[0] % TILE == 0 and im.size[1] % TILE == 0, (name, im.size)
    return im

def crop_tiles(im, tx, ty, tw=1, th=1):
    """tx,ty = top-left tile coords; tw,th = size in tiles."""
    box = (tx * TILE, ty * TILE, (tx + tw) * TILE, (ty + th) * TILE)
    return im.crop(box)

def upscale(im):
    return im.resize((im.width * SCALE, im.height * SCALE), Image.NEAREST)

def save_tile(name, im):
    path = os.path.join(OUT, name + ".png")
    upscale(im).save(path)
    print("wrote", name, im.size, "->", upscale(im).size)
    return path

# --- Terrain ---
spring = load("spring")
save_tile("T_Dirt", crop_tiles(spring, 3, 2, 1, 1))
save_tile("T_DirtEdge", crop_tiles(spring, 0, 2, 1, 1))  # dirt with grass border sample
# Water: take center of a pond fill - try (1,9) inside pond at (0,8)-(2,10)
save_tile("T_Water", crop_tiles(spring, 1, 9, 1, 1))
# Water edge / bank stone: (0,8) pond corner
save_tile("T_WaterBank", crop_tiles(spring, 0, 8, 1, 1))
# Bridge horizontal segment from spring (11,1) area
save_tile("T_Bridge", crop_tiles(spring, 11, 1, 2, 2))
# Stone stairs (11,4)
save_tile("T_Stairs", crop_tiles(spring, 11, 4, 1, 1))
# Cliff/terrace plateau grass top (6,3) and wall (6,5)
save_tile("T_TerraceTop", crop_tiles(spring, 6, 3, 1, 1))
save_tile("T_CliffFace", crop_tiles(spring, 6, 5, 1, 1))

# --- Buildings: house ~ (0,0)-(4,5) = 5x6 ---
bldg = load("buildings")
save_tile("T_House", crop_tiles(bldg, 0, 0, 5, 6))
# Fence segments (0,6)-(2,6)
save_tile("T_FenceH", crop_tiles(bldg, 0, 6, 1, 1))
save_tile("T_FenceH2", crop_tiles(bldg, 1, 6, 1, 1))
# Chest / shipping (5,1)
save_tile("T_Crate", crop_tiles(bldg, 5, 1, 1, 2))
# Lamp (5,4) tall - 1x3?
save_tile("T_Lamp", crop_tiles(bldg, 5, 4, 1, 3))
# Mailbox - may not exist; use sign (4,8) as stand-in or small prop
save_tile("T_Sign", crop_tiles(bldg, 4, 8, 1, 2))

# --- Details: trees, rocks, flowers ---
det = load("details")
# Green round tree (5,6)-(7,8)
save_tile("T_TreeRound", crop_tiles(det, 5, 6, 3, 3))
# Pine / conifer (5,9)-(7,11)
save_tile("T_TreePine", crop_tiles(det, 5, 9, 3, 3))
# Pink blossom tree (1,6)-(3,8)
save_tile("T_TreePink", crop_tiles(det, 1, 6, 3, 3))
# Rocks (1,4)-(2,5)
save_tile("T_RockLarge", crop_tiles(det, 1, 4, 2, 2))
save_tile("T_RockSmall", crop_tiles(det, 0, 4, 1, 1))
# Stump (5,4)-(6,5) approx
save_tile("T_Stump", crop_tiles(det, 5, 4, 2, 2))
# Flowers - pink bush (4,6)-(4,8) or yellow (0,6)
save_tile("T_FlowerPink", crop_tiles(det, 4, 6, 1, 3))
save_tile("T_FlowerYellow", crop_tiles(det, 0, 6, 1, 1))
# Reeds (7,13)
save_tile("T_Reed", crop_tiles(det, 7, 13, 1, 1))
# Fence from details (9,0) horizontal
save_tile("T_FenceDetail", crop_tiles(det, 9, 0, 1, 1))
save_tile("T_FencePost", crop_tiles(det, 8, 0, 1, 1))

# --- Orchard leafy tree alternate ---
orch = load("orchard")
# Standard leafy ~ cols 5-7, rows ~0-2 (3x3)
save_tile("T_TreeOrchard", crop_tiles(orch, 5, 0, 3, 3))

# --- Crops decorative (mature stages) ---
crops = load("crops")
# Save a few mature crop sprites - typically growth columns. Use dense sheet for fuller look.
dense = load("crops_dense")
# Take 3x3 mature patches as decorative beds - coords guess from typical layout
# Row of mature plants: try several and keep good ones
for i, (x, y) in enumerate([(0, 4), (4, 4), (8, 4), (12, 4)]):
    save_tile("T_CropBed{}".format(i), crop_tiles(dense, x, y, 3, 3))
# Single mature plant tiles from crops sheet
for i, (x, y) in enumerate([(2, 3), (6, 3), (10, 3), (14, 3)]):
    save_tile("T_Crop{}".format(i), crop_tiles(crops, x, y, 1, 1))

# Preview montage of key tiles
keys = ["T_Dirt", "T_Water", "T_House", "T_TreeRound", "T_TreePine", "T_RockLarge",
        "T_FenceH", "T_Crate", "T_Lamp", "T_Bridge", "T_CropBed0", "T_CropBed1"]
thumbs = []
for k in keys:
    p = os.path.join(OUT, k + ".png")
    if os.path.isfile(p):
        t = Image.open(p).convert("RGBA")
        # pad to 256
        canvas = Image.new("RGBA", (256, 256), (40, 40, 40, 255))
        t.thumbnail((240, 240), Image.NEAREST)
        canvas.paste(t, ((256 - t.width)//2, (256 - t.height)//2), t)
        thumbs.append(canvas)
if thumbs:
    cols = 4
    rows = (len(thumbs) + cols - 1) // cols
    mont = Image.new("RGBA", (cols * 256, rows * 256), (20, 20, 20, 255))
    for i, t in enumerate(thumbs):
        mont.paste(t, ((i % cols) * 256, (i // cols) * 256))
    mont_path = os.path.join(PREV, "scene_tiles_preview.png")
    mont.save(mont_path)
    print("preview", mont_path)

print("DONE slice")
