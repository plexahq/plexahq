# 3D test: The Last Day of the Dinosaurs

A 12.5-second real-3D test of the film, rendered with Blender (the `bpy` Python
module) and Cycles on the CPU. Output: [`../final/test_3d.mp4`](../final/test_3d.mp4).

**Story beat:** an explorer walks into a prehistoric clearing and looks around in
wonder. The ground shakes and birds flee. A T-Rex steps out between the trees and
roars, and the explorer screams and runs for it.

## Pieces

- `character.py`: the original hero, modelled entirely in code: big head with large glossy
  eyes and eyelids, brows, a mouth that opens, messy hair, a red-orange jacket, an olive
  backpack, jeans and boots. The rig is a chain of empties, and its joint angles come from
  the 2D stickman poses (`engine/stickman.py`), so walk and sprint cycles keep their IK
  feet.
- `trex.py`: the T-Rex body is a metaball (ellipsoids along the spine melt into one skin;
  the legs are capsules), driven every frame by the 2D theropod rig (`engine/dino.py`).
  The skull and jaw are lofted from the same 2D profiles, with teeth, amber eyes and a
  hinged jaw. Skin colour, stripes and scales are procedural shaders.
- `world.py`: terrain, about 55,000 grass clumps and 1,100 ferns (particle instancing),
  giant trees, tree ferns, rocks, an instanced forest belt, distant mountains and a
  volcano, a physical sky and a warm sun.
- `test_scene.py`: timeline, poses, facial expressions, four camera set-ups and the
  render loop.
- `audio_test.py`: sound, including the character's non-verbal reactions (`ooh`, gasp,
  whimper, shaky breaths, scream, panting). These are formant-synthesised in
  `../audio/synth.py`, alongside footsteps on the gait contacts, T-Rex steps and roar,
  ambience and music.

## Reproduce

```bash
pip install bpy numpy scipy skia-python
```

```bash
python3 film3d/audio_test.py
```

```bash
python3 film3d/test_scene.py --start 0 --end 12.5 --scale 0.75 --samples 8 --out film3d/frames
```

```bash
python3 film3d/make_video.py
```

On 4 CPU cores a frame takes about 30–60 s at 1440×810. The frames are upscaled to 1920×1080
when encoding.
