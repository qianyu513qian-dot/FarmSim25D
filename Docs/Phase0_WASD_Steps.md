# FarmSim25D 阶段0 WASD（已接线验收中）

BP_TopDownCharacter Event Graph 正确接法：
- EnhancedInputAction IA_Move (Triggered) → Add Movement Input → Add Movement Input
- Action Value → Break Vector 2D
- Get Actor Right Vector → 第1个 World Direction；Break.X → Scale Value
- Get Actor Forward Vector → 第2个 World Direction；Break.Y → Scale Value
IMC: W Swizzle YXZ; S Negate+Swizzle YXZ; A Negate; D 无修饰器
