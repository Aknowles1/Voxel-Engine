from settings import SEED
from numba import njit
from opensimplex.internals import _noise2, _noise3, _init
import numpy as np

perm, perm_grad_index3 = _init(seed=SEED)

if SEED == 0:
    rando = np.random.randint(0, 20000)
    perm, perm_grad_index3 = _init(rando)
else:
    perm, perm_grad_index3 = _init(seed=SEED)


@njit(cache=False)
def noise2(x, y):
    return _noise2(x, y, perm)


@njit(cache=False)
def noise3(x, y, z):
    return _noise3(x, y, z, perm, perm_grad_index3)
