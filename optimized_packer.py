import math
import random
import time
import numpy as np
from shapely.geometry import Polygon
from shapely import affinity
import shapely.ops
from tree_geometry import Tree

class Packer:
    def __init__(self, n_trees):
        self.n_trees = n_trees
        self.trees = []
        self.init_population()

    def init_population(self):
        # Initialize in a grid to ensure valid start (mostly)
        # Approximate size of tree is 1.5 height, 1.4 width
        spacing = 1.5
        grid_side = math.ceil(math.sqrt(self.n_trees))
        for i in range(self.n_trees):
            r = i // grid_side
            c = i % grid_side
            self.trees.append(Tree(c * spacing, r * spacing, 0))

    def get_polygons(self):
        return [t.get_polygon() for t in self.trees]

    def current_score(self):
        # Metric: (max_side)^2 / n
        # But during optimization, simplified to just bounding box side or area.
        min_x = min(t.x for t in self.trees) # Simplified center check
        max_x = max(t.x for t in self.trees)
        min_y = min(t.y for t in self.trees)
        max_y = max(t.y for t in self.trees)
        
        # We really want the bounding box of the POLYGONS, not centers.
        # But centers are faster. Let's use exact bounding box for final check.
        
        all_polys = self.get_polygons()
        
        # Quick bounds
        bounds = [p.bounds for p in all_polys]
        min_x = min(b[0] for b in bounds)
        min_y = min(b[1] for b in bounds)
        max_x = max(b[2] for b in bounds)
        max_y = max(b[3] for b in bounds)
        
        width = max_x - min_x
        height = max_y - min_y
        side = max(width, height)
        
        return side**2 # Minimize area of the bounding square

    def check_overlap(self):
        polys = self.get_polygons()
        # STRtree or simple loop
        # Simple loop for now
        total_overlap = 0.0
        for i in range(len(polys)):
            for j in range(i + 1, len(polys)):
                if polys[i].intersects(polys[j]):
                    total_overlap += polys[i].intersection(polys[j]).area
        return total_overlap

    def step(self, temp):
        # Mutate one tree
        idx = random.randint(0, self.n_trees - 1)
        tree = self.trees[idx]
        
        old_x, old_y, old_deg = tree.x, tree.y, tree.deg
        
        # Adaptive move size based on temp
        move_scale = temp * 2.0
        rot_scale = temp * 180.0
        
        tree.x += random.uniform(-move_scale, move_scale)
        tree.y += random.uniform(-move_scale, move_scale)
        tree.deg += random.uniform(-rot_scale, rot_scale)
        tree.polygon = tree._update_polygon() # Update cached poly
        
        return idx, old_x, old_y, old_deg

    def revert(self, idx, old_x, old_y, old_deg):
        tree = self.trees[idx]
        tree.x = old_x
        tree.y = old_y
        tree.deg = old_deg
        tree.polygon = tree._update_polygon()

    def optimize(self, iterations=1000, start_temp=1.0, cooling=0.99):
        current_energy = self.current_score() + (self.check_overlap() * 10000) # Heavy penalty
        best_energy = current_energy
        temp = start_temp
        
        for i in range(iterations):
            idx, ox, oy, od = self.step(temp)
            
            overlap = self.check_overlap()
            score = self.current_score()
            
            new_energy = score + (overlap * 10000)
            
            exponent = (current_energy - new_energy) / max(temp, 1e-5)
            if exponent > 700: # math.exp overflow limit is around 709
                prob = float('inf')
            else:
                prob = math.exp(exponent)
            
            if new_energy < current_energy or random.random() < prob:
                current_energy = new_energy
                if current_energy < best_energy:
                    best_energy = current_energy
                    print(f"Iter {i}: New Best {best_energy:.4f} (Overlap: {overlap:.4f})")
            else:
                self.revert(idx, ox, oy, od)
            
            temp *= cooling
            
        return best_energy

if __name__ == "__main__":
    # Test run
    packer = Packer(5)
    print("Initial Score:", packer.current_score())
    packer.optimize(iterations=5000)
