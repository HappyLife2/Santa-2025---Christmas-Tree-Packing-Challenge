import os
import subprocess
import csv
import time
import math
import argparse
from concurrent.futures import ThreadPoolExecutor

# Configuration
BINARY_NAME = "./single_group_optimizer"
SOURCE_NAME = "single_group_optimizer.cpp"
SUBMISSION_FILE = "submission.csv"
OUTPUT_FILE = "submission.csv" # Overwrite by default to save progress
COMPILE_CMD = f"g++ -O3 -march=native -std=c++17 -o {BINARY_NAME} {SOURCE_NAME}"

def compile_optimizer():
    """Compiles the C++ optimizer."""
    print(f"Compiling {SOURCE_NAME}...")
    try:
        subprocess.check_call(COMPILE_CMD, shell=True)
        print("Compilation successful.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Compilation failed: {e}")
        return False

def load_scores(filename):
    """Loads scores (area) for each N from the CSV file."""
    scores = {}
    if not os.path.exists(filename):
        print(f"Error: {filename} not found.")
        return scores
    
    # We need to parse strict 's' prefixed floats if present
    # But actually, the C++ code reads numeric values even with 's' prefix logic handled manually?
    # Let's write a robust parser similar to the C++ one or just use the structure.
    # The file format is id,x,y,deg. ID is n_i.
    
    data = {} # n -> list of items
    
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                id_str = row['id']
                n_str, i_str = id_str.split('_')
                n = int(n_str)
                
                # Helper to strip 's' if exists
                def val(x): return float(x[1:]) if x.startswith('s') else float(x)
                
                x = val(row['x'])
                y = val(row['y'])
                # deg is not needed for score calc (area) but good to have if we did full recalc
                # For now, we only need min/max x/y to calc area.
                
                if n not in data:
                    data[n] = {'min_x': 1e9, 'max_x': -1e9, 'min_y': 1e9, 'max_y': -1e9, 'count': 0}
                
                # Approximate bounding box logic? 
                # Wait, the C++ code calculates exact polygon extrema. 
                # Doing that in Python is slow and duplicates code.
                # BETTER APPROACH: Run the optimizer with 0 iterations to get the score!
                # OR, just trust the C++ optimizer to report the initial score.
                pass 
                
            except ValueError:
                continue
    
    return data

def run_optimizer_for_group(n, iterations=5000, restarts=4):
    """Runs the C++ optimizer for a specific group N."""
    env = os.environ.copy()
    env["GROUP_NUMBER"] = str(n)
    
    cmd = [
        BINARY_NAME, 
        "-i", SUBMISSION_FILE, 
        "-o", OUTPUT_FILE, 
        "-n", str(iterations), 
        "-r", str(restarts)
    ]
    
    print(f"[{n}] Starting optimization (Iter: {iterations}, Restarts: {restarts})...")
    start_time = time.time()
    
    try:
        # Capture stdout to see if it improved
        result = subprocess.run(
            cmd, 
            env=env, 
            capture_output=True, 
            text=True
        )
        
        duration = time.time() - start_time
        output = result.stdout
        
        # Check for improvement message
        # The C++ code prints "IMPROVEMENT! New score: ..." if it writes?
        # Actually checking the C++ code:
        # It loads, optimizes, and expects to WRITE to 'out'.
        # It doesn't seem to rewrite the WHOLE file, just the group?
        # Wait, the `saveCSV` function in C++ iterates 1..200 and writes ALL.
        # This implies the C++ tool is designed to read the whole file and write the whole file.
        # THIS IS DANGEROUS FOR CONCURRENCY.
        # If we run multiple in parallel, they will overwrite each other's changes to other groups.
        
        # FIX: We can only run ONE instance at a time if the C++ tool rewrites the whole file.
        # Unless we modify the C++ tool to output just the lines for this group, 
        # and we integrate them in Python.
        
        # For now, let's run SEQUENTIALLY to be safe, or just use the tool's internal parallelism (OpenMP).
        # The tool uses OpenMP, so it's already using multiple cores for ONE group.
        # So running sequentially by group is actually efficient for CPU usage.
        
        if result.returncode != 0:
            print(f"[{n}] Failed: {result.stderr}")
            return
            
        print(f"[{n}] Finished in {duration:.2f}s.")
        
        improved = False
        for line in output.splitlines():
            if "IMPROVED" in line or "New best" in line:
                print(f"[{n}] \033[92m{line}\033[0m")
                improved = True
            elif "Initial score" in line:
                print(f"[{n}] {line}")
                
        # Adaptive Strategy: If no improvement and iterations were low, boost them next time?
        # Or better: return status to caller to decide.
        return improved

    except Exception as e:
        print(f"[{n}] Error execution: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Manager for Santa 2025 Optimizer")
    parser.add_argument("--groups", type=str, help="Comma-separated list of N to optimize (e.g., '1,2,3' or '1-10')")
    parser.add_argument("--iter", type=int, default=10000, help="Total iterations per cycle (shared across threads)")
    parser.add_argument("--restarts", type=int, default=16, help="Number of Replica Exchange cycles (formerly restarts)")
    parser.add_argument("--loop", action="store_true", help="Infinite loop over groups")
    parser.add_argument("--score", action="store_true", help="Calculate total score of the submission file")
    
    args = parser.parse_args()
    
    if args.score:
        print(f"Calculating score for {SUBMISSION_FILE}...")
        try:
            total_score = 0.0
            # Read all coords
            groups = {} # n -> list of (x,y)
            with open(SUBMISSION_FILE, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        id_str = row['id']
                        n, i = map(int, id_str.split('_'))
                        
                        def val(x): return float(x[1:]) if x.startswith('s') else float(x)
                        
                        x = val(row['x'])
                        y = val(row['y'])
                        
                        if n not in groups: groups[n] = []
                        groups[n].append((x, y))
                    except ValueError:
                        continue
            
            # Constants for polygon (approximate for bounding box check)
            # To be exact we need the polygon vertices. 
            # Replicating getPoly logic from C++
            TX = [0, 0.125, 0.0625, 0.2, 0.1, 0.35, 0.075, 0.075, -0.075, -0.075, -0.35, -0.1, -0.2, -0.0625, -0.125]
            TY = [0.8, 0.5, 0.5, 0.25, 0.25, 0, 0, -0.2, -0.2, 0, 0, 0.25, 0.25, 0.5, 0.5]
            PI = 3.14159265358979323846
            
            for n in range(1, 201):
                if n not in groups:
                    print(f"Missing N={n}")
                    continue
                    
                pts = groups[n]
                # Calculate global bounds for this group
                gx0, gy0, gx1, gy1 = 1e9, 1e9, -1e9, -1e9
                
                # For each tree, get its bounds. 
                # Note: We don't have rotation (deg) in the simple list above?? 
                # Wait, we need 'deg' to calculate exact bounds!
                # I missed capturing 'deg' in the read loop above.
                pass 
                
        except Exception:
            pass
            
        # Let's retry reading WITH deg
        groups = {}
        with open(SUBMISSION_FILE, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                id_str = row['id']
                n, i = map(int, id_str.split('_'))
                def val(x): return float(x[1:]) if x.startswith('s') else float(x)
                if n not in groups: groups[n] = []
                groups[n].append((val(row['x']), val(row['y']), val(row['deg'])))
        
        TX = [0, 0.125, 0.0625, 0.2, 0.1, 0.35, 0.075, 0.075, -0.075, -0.075, -0.35, -0.1, -0.2, -0.0625, -0.125]
        TY = [0.8, 0.5, 0.5, 0.25, 0.25, 0, 0, -0.2, -0.2, 0, 0, 0.25, 0.25, 0.5, 0.5]
        PI = 3.14159265358979323846
        
        total_norm_area = 0.0
        
        for n in range(1, 201):
            if n not in groups:
                 # Penalty or ignore? Challenge says 1-200 required.
                 print(f"N={n} missing!")
                 continue
            
            min_x, max_x = 1e9, -1e9
            min_y, max_y = 1e9, -1e9
            
            for (x, y, d) in groups[n]:
                rad = d * (PI / 180.0)
                s, c = math.sin(rad), math.cos(rad)
                for k in range(15):
                    # Rotate and translate
                    px = TX[k] * c - TY[k] * s + x
                    py = TX[k] * s + TY[k] * c + y
                    min_x = min(min_x, px)
                    max_x = max(max_x, px)
                    min_y = min(min_y, py)
                    max_y = max(max_y, py)
            
            side = max(max_x - min_x, max_y - min_y)
            score = (side * side) / n
            total_norm_area += score
            
        print(f"Total Normalized Area Score: {total_norm_area:.6f}")
        return

    if not compile_optimizer():
        return

    # Determine groups to process
    groups_to_process = []
    if args.groups:
        parts = args.groups.split(',')
        for p in parts:
            if '-' in p:
                s, e = map(int, p.split('-'))
                groups_to_process.extend(range(s, e + 1))
            else:
                groups_to_process.append(int(p))
    else:
        # Default: Process all 1-200? Or just a subset?
        # Maybe reverse order? Larger N are harder.
        # Or prioritized list based on score analysis.
        groups_to_process = list(range(1, 201))
    
    # Check for submission file
    if not os.path.exists(SUBMISSION_FILE):
        print(f"Warning: {SUBMISSION_FILE} not found. Creating empty/dummy if needed?")
        # The C++ tool might crash if file missing.
        # We assume the user creates it. 
        pass

    print(f"Processing {len(groups_to_process)} groups...")
    
    # Track "difficulty" or "stagnation" per group
    stagnation = {n: 0 for n in groups_to_process}
    
    while True:
        for n in groups_to_process:
            # Scale parameters based on stagnation
            current_iter = args.iter + (stagnation[n] * 2000)
            current_restarts = args.restarts + (stagnation[n] // 2)
            
            improved = run_optimizer_for_group(n, current_iter, current_restarts)
            
            if improved:
                print(f"[{n}] Improved! Resetting stagnation.")
                stagnation[n] = 0
            else:
                stagnation[n] += 1
                # Cap stagnation to avoid explosion
                if stagnation[n] > 10: stagnation[n] = 10
            
        if not args.loop:
            break
        print("--- Loop finished, restarting sequence ---")

if __name__ == "__main__":
    main()
