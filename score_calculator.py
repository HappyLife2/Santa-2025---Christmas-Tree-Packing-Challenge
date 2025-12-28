import csv
import math
from tree_geometry import Tree
from shapely.geometry import box

def calculate_score():
    configs = {}
    
    # Read CSV
    try:
        with open('submission.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                id_str = row['id']
                n = int(id_str.split('_')[0])
                idx = int(id_str.split('_')[1])
                
                # Strip 's'
                raw_x = row['x'].replace('s', '')
                raw_y = row['y'].replace('s', '')
                raw_deg = row['deg'].replace('s', '')
                
                if not raw_x or not raw_y:
                    print(f"Warning: Invalid data at {id_str}")
                    continue
                    
                x = float(raw_x)
                y = float(raw_y)
                deg = float(raw_deg)
                
                deg = float(raw_deg)
                
                if n not in configs:
                    configs[n] = []
                configs[n].append(Tree(x, y, deg))
                
    except FileNotFoundError:
        print("submission.csv not found")
        return

    if len(configs) < 200:
        print(f"ERROR: Only found {len(configs)} groups! Scoring is invalid.")
        missing = [n for n in range(1, 201) if n not in configs]
        print(f"Missing: {missing}")
        return

    total_score = 0.0
    
    scores_list = []
    
    # Calculate for each N
    for n, trees in configs.items():
        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')
        
        for tree in trees:
            poly = tree.get_polygon()
            xmin, ymin, xmax, ymax = poly.bounds
            min_x = min(min_x, xmin)
            min_y = min(min_y, ymin)
            max_x = max(max_x, xmax)
            max_y = max(max_y, ymax)
            
        side = max(max_x - min_x, max_y - min_y)
        score_n = (side * side) / n
        total_score += score_n
        
        scores_list.append((n, score_n))

    print(f"Total Combined Score: {total_score:.6f}")
    
    # Sort by score descending (Worst offenders first)
    scores_list.sort(key=lambda x: x[1], reverse=True)
    
    print("\nTop 20 Worst Groups (Highest Norm Area):")
    for n, s in scores_list[:20]:
        print(f"N={n}: {s:.6f}")
        
    # Also sort by 'Efficiency' (Metric / Theoretical Min Area) if we want?
    # Actually raw Metric is what matters for the sum.
    # N=1 score is ~0.66. N=200 score is ~0.35.
    # So small N contributes MORE to the total score per unit.
    # Optimizing N=1, N=2, N=3 yields BIG points.
    # E.g. reducing N=1 from 0.66 to 0.60 saves 0.06.
    # Reducing N=200 from 0.35 to 0.30 saves 0.05.
    # So yes, generally Small N are high value targets.

if __name__ == '__main__':
    calculate_score()
