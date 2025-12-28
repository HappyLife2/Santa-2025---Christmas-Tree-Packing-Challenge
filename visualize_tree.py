import matplotlib.pyplot as plt
from shapely.geometry import Polygon
import sys
import csv
import os
from tree_geometry import Tree, get_placeholder_tree_coords

def plot_tree_shape():
    coords = get_placeholder_tree_coords()
    poly = Polygon(coords)
    x, y = poly.exterior.xy

    fig, ax = plt.subplots()
    ax.plot(x, y, color='green')
    ax.fill(x, y, color='lightgreen')
    
    # Mark the origin (0,0) - center of trunk top
    ax.plot(0, 0, 'ro', label='Origin (0,0)')
    
    ax.set_aspect('equal')
    ax.set_title("Placeholder Christmas Tree Geometry")
    ax.legend()
    plt.grid(True)
    plt.savefig("tree_shape.png")
    print("Tree shape saved to tree_shape.png")

def plot_trees(trees, filename):
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_aspect('equal')
    
    # Track bounds
    min_x, max_x = 1e9, -1e9
    min_y, max_y = 1e9, -1e9
    
    for tree in trees:
        poly = tree.get_polygon()
        # Plot
        x, y = poly.exterior.xy
        ax.fill(x, y, alpha=0.5, edgecolor='black')
        
        # update bounds
        bounds = poly.bounds
        min_x = min(min_x, bounds[0])
        min_y = min(min_y, bounds[1])
        max_x = max(max_x, bounds[2])
        max_y = max(max_y, bounds[3])
        
    # Draw Bounding Box
    width = max_x - min_x
    height = max_y - min_y
    side = max(width, height)
    rect = plt.Rectangle((min_x, min_y), side, side, fill=False, edgecolor='red', linewidth=2)
    ax.add_patch(rect)
    
    ax.set_xlim(min_x - 1, max_x + 1)
    ax.set_ylim(min_y - 1, max_y + 1)
    
    plt.title(f"Packing (Side={side:.4f})")
    plt.savefig(filename)
    print(f"Saved {filename}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python visualize_tree.py <N_or_Filename>")
        sys.exit(1)
        
    arg = sys.argv[1]
    trees = []
    
    if os.path.isfile(arg):
        # Load Raw CSV
        filename = arg
        print(f"Loading raw file {filename}...")
        with open(filename, 'r') as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                # id, x, y, deg
                try:
                    trees.append(Tree(float(row[1]), float(row[2]), float(row[3])))
                except:
                    pass
        plot_trees(trees, filename + ".png")
        sys.exit(0)
    
    # N mode
    try:
        target_n = int(arg)
    except ValueError:
        print("Argument must be integer N or filename")
        sys.exit(1)
        
    # Load submission
    try:
        with open('submission.csv', 'r') as f:
            reader = csv.reader(f)
            next(reader) # Skip header
            for row in reader:
                # id, sX, sY, sDeg
                row_id = row[0]
                parts = row_id.split('_')
                n = int(parts[0])
                
                if n == target_n:
                    x = float(row[1].replace('s', ''))
                    y = float(row[2].replace('s', ''))
                    deg = float(row[3].replace('s', ''))
                    trees.append(Tree(x, y, deg))
    except FileNotFoundError:
        print("submission.csv not found!")
        sys.exit(1)
        
    if not trees:
        print(f"No trees found for N={target_n}")
        sys.exit(1)
        
    print(f"Visualizing N={target_n} with {len(trees)} trees...")
    plot_trees(trees, f"packing_n{target_n}.png")
