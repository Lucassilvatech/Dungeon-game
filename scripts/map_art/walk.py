"""Eight authored full-body walking poses retaining approved heads and palettes.

Each pose redraws the torso silhouette, shoulder line, articulated arms/knees and
grounded boots. No split-in-half translation of a finished character. The head
pixels are retained from the approved directional designs (identity preservation).
"""

from PIL import Image, ImageDraw

# Contact, recoil, passing, rise; then the opposite leg. One foot always supports
# the body. One logical pixel = two display pixels. Arms counter the forward leg.
SWING = (-2, -1, 0, 1, 2, 1, 0, -1)
LIFT = (0, 0, 1, 1, 0, 0, 0, 0)


def walk_pose(pose, direction, step):
    source = pose.resize((16, 24), Image.Resampling.NEAREST)
    im = Image.new("RGBA", (24, 32))
    d = ImageDraw.Draw(im)
    dark = source.getpixel((3, 2))
    shirt = source.getpixel((8, 13))
    shadow = tuple(max(0, c - 16) for c in shirt[:3]) + (255,)
    skin = (
        source.getpixel((8, 8))
        if direction in (0, 3)
        else source.getpixel((5 if direction == 1 else 10, 7))
    )
    # Back-facing heads are hair: hands still use the approved peach palette.
    if direction == 3 or max(skin[:3]) < 130:
        skin = (250, 198, 157, 255)
    sleeve = (247, 227, 196, 255)
    pants = (54, 48, 55, 255)
    boot = (48, 34, 32, 255)
    belt = (68, 47, 44, 255)
    swing = SWING[step % 8]
    bob = 1 if step % 4 == 1 else 0
    lean = -1 if step in (1, 2) else 1 if step in (5, 6) else 0
    # Same 32x48 design, centred in 48x64 cell; planted feet end at display y=62.
    hip_y, shoulder_y = 24 + bob, 18 + bob

    def limb(points, colour, width=3):
        d.line(points, fill=dark, width=width + 2)
        d.line(points, fill=colour, width=width)

    if direction in (0, 3):
        # Depth change in frontal gait: one knee bends and shortens while the
        # support boot stays at the ground line. Distinct upper/lower segments.
        for side in (-1, 1):
            sx = 12 + side * 3
            forward = swing * side
            lift = max(0, forward)
            foot_y = 30 - lift
            knee_x = sx + (side if forward < 0 else 0)
            limb([(sx, hip_y), (knee_x, 27), (sx, foot_y - 1)], pants, 3)
            d.rectangle((sx - 2, foot_y - 1, sx + 1, foot_y), fill=boot)
            if lift:
                d.point((sx - 1, foot_y - 2), fill=(88, 68, 60, 255))
        torso = [
            (7 + lean, shoulder_y),
            (16 + lean, shoulder_y + (step % 2)),
            (16, hip_y),
            (7, hip_y),
        ]
        d.polygon(torso, fill=dark)
        d.polygon(
            [
                (8 + lean, shoulder_y),
                (15 + lean, shoulder_y + (step % 2)),
                (15, hip_y - 1),
                (8, hip_y - 1),
            ],
            fill=shirt,
        )
        d.line((8 + lean, shoulder_y + 1, 8, hip_y - 2), fill=shadow)
        for side in (-1, 1):
            sx = 12 + side * 6 + lean
            arm = -swing * side
            elbow = (sx + (side if arm > 0 else 0), 21 + bob + arm // 2)
            wrist = (sx + (-side if arm < 0 else 0), 24 + arm)
            limb([(sx, shoulder_y + 1), elbow], sleeve, 2)
            limb([elbow, wrist], skin, 2)
        d.line((8, hip_y - 1, 15, hip_y - 1), fill=belt, width=2)
        if direction == 0:
            d.rectangle((11, hip_y - 2, 12, hip_y - 1), fill=(248, 203, 118, 255))
        # Head retains every approved facial/hair pixel; small shoulder lean only.
        im.alpha_composite(source.crop((0, 0, 16, 11)), (4 + lean, 7 + bob))
    else:
        facing = -1 if direction == 1 else 1
        # Rear arm/leg drawn first, front limbs after torso; elbows and knees
        # rotate through passing and contact rather than translating rectangles.
        for side in (-1, 1):
            travel = swing * side
            knee_x = 12 + travel * facing
            foot_x = 12 + (travel * 2) * facing
            lift = 2 if side * swing > 0 and step % 4 in (2, 3) else 0
            limb([(12, hip_y), (knee_x, 27 - lift), (foot_x, 29 - lift)], pants, 3)
            d.rectangle((foot_x - 2, 29 - lift, foot_x + 2, 30 - lift), fill=boot)
        far_arm = -swing * facing
        limb(
            [(12, shoulder_y), (12 - far_arm, 21 + bob), (12 - far_arm * 2, 24 + bob)],
            shadow,
            2,
        )
        d.polygon(
            [
                (9 + lean, shoulder_y),
                (15 + lean, shoulder_y + 1),
                (15, hip_y),
                (9, hip_y),
            ],
            fill=dark,
        )
        d.polygon(
            [
                (10 + lean, shoulder_y),
                (14 + lean, shoulder_y + 1),
                (14, hip_y - 1),
                (10, hip_y - 1),
            ],
            fill=shirt,
        )
        d.line((10, hip_y - 1, 14, hip_y - 1), fill=belt, width=2)
        elbow = (12 + far_arm, 21 + bob)
        hand = (12 + far_arm * 2, 24 - abs(swing) // 2 + bob)
        limb([(12 + lean, shoulder_y + 1), elbow], sleeve, 2)
        limb([elbow, hand], skin, 2)
        im.alpha_composite(source.crop((0, 0, 16, 11)), (4 + lean, 7 + bob))
    return im.resize((48, 64), Image.Resampling.NEAREST)
