from WebCamEnhancer.core import utils
import numpy as np
import pytest


def test_resolve_xy_center():
    # no changes to top
    assert ((6,1,10,20), (0,0,10,20))==utils.resolve_xy_center((20,10),(50,40), center=(11,11))
    # cut begining of image
    assert ((0,0,10,3), (10,2,20,5))==utils.resolve_xy_center((5,20),(41,41), center=(0,0))
    # cut end of image
    assert ((35,34,5,6), (0,0,5,6))==utils.resolve_xy_center((10,6),(40,40), center=(38,39))
    # mixup in coordinates
    assert ((36,33,4,9), (0,0,4,9))==utils.resolve_xy_center((10,6),(42,40), center=(39,38))
