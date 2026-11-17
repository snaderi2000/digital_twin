"""Deterministic camera choreography, expressed in local metres."""
from math import cos, pi

FPS = 24
PITCH = (297.76 - 10.0) / 33
SHOTS = [
    dict(name='River approach', seconds=6, start=(-102,-92,10), end=(-66,-40,8),
         look_start=(-26,0,5.7), look_end=(-20,0,6), lens=38),
    dict(name='Through the river arch', seconds=5, start=(-5*PITCH,-16,3.25), end=(-5*PITCH,16,3.25),
         look_start=(-5*PITCH,14,3.25), look_end=(-5*PITCH,46,3.25), lens=24),
    dict(name='Upper promenade', seconds=5, start=(-104,-.7,8.35), end=(-78,-.7,8.35),
         look_start=(-74,0,8.65), look_end=(-48,0,8.65), lens=26),
    dict(name='Lower gallery', seconds=4, start=(-112,0,2.65), end=(-98,0,2.65),
         look_start=(-82,0,2.7), look_end=(-68,0,2.7), lens=22),
    dict(name='The bridge of thirty-three arches', seconds=4, start=(-165,-240,130), end=(-230,-300,220),
         look_start=(0,0,4), look_end=(0,0,4), lens=42),
]


def shot_ranges():
    start = 1
    for shot in SHOTS:
        end = start + shot['seconds'] * FPS - 1
        yield shot, start, end
        start = end + 1


def pose(shot, t):
    # Cosine easing gives zero velocity at each cut, with no overshoot into masonry.
    u = (1 - cos(pi * t)) / 2
    def lerp(a,b): return tuple(x+(y-x)*u for x,y in zip(a,b))
    return lerp(shot['start'],shot['end']), lerp(shot['look_start'],shot['look_end'])


TOTAL_FRAMES = sum(s['seconds'] * FPS for s in SHOTS)
