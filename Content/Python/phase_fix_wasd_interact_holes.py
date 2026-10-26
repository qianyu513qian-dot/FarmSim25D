# -*- coding: utf-8 -*-
"""FarmSim25D Play fix: camera-relative WASD + IMC E/F/R/G/H + fill grass holes.

Canonical runner (after probes + phase_fix_wasd_interact_holes2.py success):
  python Content/Python/run_remote.py Content/Python/phase_fix_wasd_interact_holes2.py

Also run holes3 only if verifying Self/IMC again:
  python Content/Python/run_remote.py Content/Python/phase_fix_wasd_interact_holes3.py

Results (2026-10-25):
- Move: CAMERA-RELATIVE — W/S = Normalize2D(GetForwardVector(yaw-only cam rot));
  A/D = Normalize2D(GetRightVector(...)). Via GetComponentByClass(CameraComponent).
- SpringArm: pitch=-40 yaw=-45 ortho=2800 arm=6500 (iso look; yaw no longer drives WASD).
- IMC: E Interact, F Plant, R Water, G Grow, H Harvest remapped; WASD preserved.
  (Root cause of broken E: DefaultKeyMappings had only WASD+touch.)
- Holes: 181 grass tiles filled from donor VMF_Grass mesh; hoe rect + near-PS holes gone.
- PlayerStart Grid(23,16) world(2350,1650,100); FarmCollisionFloor kept.
- VisualizeCell already chained TillCell→Soil_Dry scale 0.01; no change needed.
"""
print("See phase_fix_wasd_interact_holes2.py — this file is the index/doc.")
