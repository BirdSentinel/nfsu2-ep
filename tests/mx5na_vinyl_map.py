"""Check the NA-to-NB atlas orientation using the locally owned models."""
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from mx5na_vinyl_map import make_map

game = Path(sys.argv[1])
mapping = make_map(game / 'CARS/MX5NA/GEOMETRY.BIN', game / 'CARS/MIATA/GEOMETRY.BIN')

def at(u, v):
    result = mapping[int(v*512), int(u*512)]
    assert np.isfinite(result).all(), (u, v, result)
    return result

# The NA hood's longitudinal UV runs backwards relative to the NB's.
hood_rear, hood_front = at(.40, .65), at(.25, .65)
assert hood_front[0] > hood_rear[0] + .15
assert abs(hood_front[1]-hood_rear[1]) < .01
assert at(.35, .74)[1] < at(.35, .56)[1]  # lateral orientation
# Door graphics belong in the two side strips, not on the hood/roof.
left, right = at(.574, .906), at(.574, .394)
assert .48 < left[0] < .52 and .10 < left[1] < .16
assert .48 < right[0] < .52 and .63 < right[1] < .70
print('PASS hood orientation, bilateral side strips and finite surface coverage')
