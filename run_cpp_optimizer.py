import subprocess
import shutil
import hashlib
import os
import sys
import time
import random

# User's logic adapted
    
def main():
    # Make sure we have the latest submission file
    if not os.path.exists("submission.csv"):
        if os.path.exists("submission_external.csv"):
            shutil.copy("submission_external.csv", "submission.csv")
        else:
            print("No submission.csv found!")
            return

    # Target the "Worst Groups" first (Highest Normalized Area)
    # Based on analysis:
    targets = [1, 2, 3, 5, 4, 7, 6, 8, 9, 14, 15, 22, 10, 21, 20, 11, 26, 16, 12, 13]
    
    # Also just loop all small N up to 50, as they have high weight
    for n in range(1, 51):
        if n not in targets:
            targets.append(n)
            
    print(f"Targeting groups: {targets}")
    
    pass_count = 1
    while True:
        print(f"\n=== STARTING PASS {pass_count} ===")
        random.shuffle(targets) # Shuffle to mix it up
        
        for n in targets:
            print(f"\nCreated aggressive job for N={n} (Pass {pass_count})")
            start_t = time.time()
            
            # Aggressive settings:
            # N=100k iterations, 64 restarts
            iter_cmd = 200000
            restarts_cmd = 64
            
            success = run_optimizer(n, restarts=restarts_cmd) 
            
            if success:
                print(f"N={n} finished pass in {time.time()-start_t:.2f}s")
            else:
                print(f"N={n} failed")
        
        pass_count += 1
        print(f"=== FINISHED PASS {pass_count-1} (looping...) ===")

def run_optimizer(n, restarts=1000):
    # Updated to accept higher iterations via command line if we change the C++ arg parsing
    # The C++ code takes -n for iterations.
    cmd = f'GROUP_NUMBER={n} ./single_group_optimizer -n 200000 -r {restarts} -i submission.csv -o submission.csv'
    print(f"Running for N={n} with 200k iters / {restarts} restart...")
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=True,
            bufsize=1,
            universal_newlines=True
        )
        
        output = []
        for line in process.stdout:
            print(line, end='')
            output.append(line)
            
        process.wait()
        
        # simple check for "Improvement:" in output
        combined = "".join(output)
        if "Improvement:" in combined and "No improvement" not in combined:
             print(f"!!! FOUND IMPROVEMENT FOR N={n} !!!")
             
        return process.returncode == 0
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == '__main__':
    main()
