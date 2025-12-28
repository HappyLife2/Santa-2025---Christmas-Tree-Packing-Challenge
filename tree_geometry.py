import numpy as np
from shapely.geometry import Polygon, Point
from shapely.affinity import rotate, translate

class Tree:
    def __init__(self, x, y, deg):
        self.x = x
        self.y = y
        self.deg = deg
        self.base_polygon = self._create_base_polygon()
        self.polygon = self._update_polygon()

    def _create_base_polygon(self):
        # Vertices extracted from single_group_optimizer.cpp (NV=15)
        # TX and TY from the user provided code:
        tx = [0, 0.125, 0.0625, 0.2, 0.1, 0.35, 0.075, 0.075, -0.075, -0.075, -0.35, -0.1, -0.2, -0.0625, -0.125]
        ty = [0.8, 0.5, 0.5, 0.25, 0.25, 0, 0, -0.2, -0.2, 0, 0, 0.25, 0.25, 0.5, 0.5]
        
        # Combine into list of (x,y)
        coords = list(zip(tx, ty))
        
        return Polygon(coords)

    def _update_polygon(self):
        # Rotate and then translate
        poly = rotate(self.base_polygon, self.deg, origin=(0, 0), use_radians=False)
        poly = translate(poly, self.x, self.y)
        return poly

    def get_polygon(self):
        return self.polygon

def get_placeholder_tree_coords():
    # Return the raw coords for visualization
    t = Tree(0, 0, 0)
    return list(t.base_polygon.exterior.coords)
