import pymunk
import math
import random
import csv
import sys
import os

# Exact Geometry from single_group_optimizer.cpp
TX = [0, 0.125, 0.0625, 0.2, 0.1, 0.35, 0.075, 0.075, -0.075, -0.075, -0.35, -0.1, -0.2, -0.0625, -0.125]
TY = [0.8, 0.5, 0.5, 0.25, 0.25, 0, 0, -0.2, -0.2, 0, 0, 0.25, 0.25, 0.5, 0.5]

def create_tree_body(space, pos, angle, body_type=pymunk.Body.DYNAMIC):
    mass = 1
    inertia = pymunk.moment_for_poly(mass, [(0,0), (0,1), (1,0)]) # Placeholder
    body = pymunk.Body(mass, inertia, body_type=body_type)
    body.position = pos
    body.angle = angle
    
    # Decompose into 4 convex shapes to form the tree
    
    # 1. Trunk (Rectangle)
    # (-0.075, -0.2) to (0.075, 0)
    trunk_shape = pymunk.Poly(body, [(-0.075, -0.2), (0.075, -0.2), (0.075, 0), (-0.075, 0)])
    trunk_shape.friction = 0.0
    trunk_shape.elasticity = 0.0
    
    # 2. Bottom Tier (Trapezoid)
    # (-0.35, 0), (0.35, 0), (0.1, 0.25), (-0.1, 0.25)
    bottom_shape = pymunk.Poly(body, [(-0.35, 0), (0.35, 0), (0.1, 0.25), (-0.1, 0.25)])
    bottom_shape.friction = 0.0
    bottom_shape.elasticity = 0.0
    
    # 3. Middle Tier (Trapezoid)
    # (-0.2, 0.25), (0.2, 0.25), (0.0625, 0.5), (-0.0625, 0.5)
    mid_shape = pymunk.Poly(body, [(-0.2, 0.25), (0.2, 0.25), (0.0625, 0.5), (-0.0625, 0.5)])
    mid_shape.friction = 0.0
    mid_shape.elasticity = 0.0

    # 4. Top Tier (Triangle)
    # (-0.125, 0.5), (0.125, 0.5), (0, 0.8)
    top_shape = pymunk.Poly(body, [(-0.125, 0.5), (0.125, 0.5), (0, 0.8)])
    top_shape.friction = 0.0
    top_shape.elasticity = 0.0
    
    space.add(body, trunk_shape, bottom_shape, mid_shape, top_shape)
    return body

def run_simulation(N, steps=8000):
    space = pymunk.Space()
    space.gravity = (0, 0)
    space.damping = 0.4 # Less damping to allow sliding
    
    tree_bodies = []
    # Start spread out but inside the initial wall box
    box_size = max(5.0, math.sqrt(N) * 2.0) 
    initial_wall_dist = box_size * 2.0
    
    for i in range(N):
        pos = (random.uniform(-box_size, box_size), random.uniform(-box_size, box_size))
        angle = random.uniform(0, 2*math.pi)
        b = create_tree_body(space, pos, angle)
        tree_bodies.append(b)
        
    # bodies = space.bodies # Do not use this, it includes walls!
    
    # Create Walls (Kinematic Bodies) - THICK BOXES to prevent tunneling
    thick = 200.0
    walls = []
    
    # Left Wall body
    l_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    l_body.position = (-initial_wall_dist - thick/2, 0)
    # Shape is box centered at body? Poly box arguments are (width, height) not helpful.
    # Poly(body, vertices). Vertices relative.
    # Box width=thick, height=2000
    l_shape = pymunk.Poly.create_box(l_body, (thick, 2000.0))
    l_shape.friction = 0.0
    space.add(l_body, l_shape)
    walls.append(l_body)
    
    # Right Wall
    r_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    r_body.position = (initial_wall_dist + thick/2, 0)
    r_shape = pymunk.Poly.create_box(r_body, (thick, 2000.0))
    r_shape.friction = 0.0
    space.add(r_body, r_shape)
    walls.append(r_body)
    
    # Bottom Wall
    b_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    b_body.position = (0, -initial_wall_dist - thick/2)
    b_shape = pymunk.Poly.create_box(b_body, (2000.0, thick))
    b_shape.friction = 0.0
    space.add(b_body, b_shape)
    walls.append(b_body)

    # Top Wall
    t_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    t_body.position = (0, initial_wall_dist + thick/2)
    t_shape = pymunk.Poly.create_box(t_body, (2000.0, thick))
    t_shape.friction = 0.0
    space.add(t_body, t_shape)
    walls.append(t_body)
    
    dt = 1.0/120.0 # Higher precision
    target_size = math.sqrt(N) * 0.35 # Very Aggressive Target (forces overlap then relaxation)
    
    # Speed: Move by (initial - target) over steps
    # dist to move = initial_wall_dist - target_size (offset by thickness/2 is handled by body pos)
    # Actually, body pos is at (dist + thick/2). We want edge at dist.
    # Current edge is at (pos.x - thick/2) for Right wall.
    # So we want body to move from (init + thick/2) to (target + thick/2).
    # Distance is same.
    
    closing_speed = (initial_wall_dist - target_size) / (steps * 0.9 * dt)
    
    for x in range(steps):
        # Move walls inwards
        # Left Wall (moves Right +)
        # Target position x = -target_size - thick/2
        if walls[0].position.x < (-target_size - thick/2):
            walls[0].velocity = (closing_speed, 0)
        else:
            walls[0].velocity = (0,0)

        # Right Wall (moves Left -)
        if walls[1].position.x > (target_size + thick/2):
            walls[1].velocity = (-closing_speed, 0)
        else:
            walls[1].velocity = (0,0)
            
        # Bottom Wall (moves Up +)
        if walls[2].position.y < (-target_size - thick/2):
            walls[2].velocity = (0, closing_speed)
        else:
            walls[2].velocity = (0,0)

        # Top Wall (moves Down -)
        if walls[3].position.y > (target_size + thick/2):
            walls[3].velocity = (0, -closing_speed)
        else:
            walls[3].velocity = (0,0)

        # Shake
        if x % 20 == 0:
            for b in tree_bodies:
                b.torque = random.uniform(-15, 15)

        space.step(dt)
        
    # Constant Squeeze Phase (keep pushing for a bit)
    for x in range(1000):
        # Keep velocity? No, stop borders and let physics settle or keep squeezing gently?
        # Let's stop borders.
        for w in walls:
             w.velocity = (0,0)
        space.damping = 0.1
        space.step(dt)

    results = []
    for b in tree_bodies:
        x, y = b.position
        rot = math.degrees(b.angle)
        rot = rot % 360.0
        results.append({'x': x, 'y': y, 'deg': rot})

    # Output Score
    min_x, max_x, min_y, max_y = 1e9, -1e9, 1e9, -1e9
    
    # Compute bounds based on bodies only
    for b in tree_bodies:
        for shape in b.shapes:
            bb = shape.cache_bb()
            min_x = min(min_x, bb.left)
            max_x = max(max_x, bb.right)
            min_y = min(min_y, bb.bottom)
            max_y = max(max_y, bb.top)
            
    width = max_x - min_x
    height = max_y - min_y
    side = max(width, height)
    score = (side * side) / N
    
    print(f"Physics Result N={N}: Side={side:.6f}, Score={score:.6f}", file=sys.stderr)

    return results

    # Calculate Bounding Box and Score
    min_x, max_x, min_y, max_y = 1e9, -1e9, 1e9, -1e9
    
    # We need to check all vertices of all shapes
    for b in bodies:
        for shape in b.shapes:
            # Pymunk shapes are in world coordinates? No, need to transform
            # shape.get_vertices() returns local vertices for Poly
            # cache_bb() updates the BB in world coords
            bb = shape.cache_bb()
            min_x = min(min_x, bb.left)
            max_x = max(max_x, bb.right)
            min_y = min(min_y, bb.bottom)
            max_y = max(max_y, bb.top)
            
    width = max_x - min_x
    height = max_y - min_y
    side = max(width, height)
    score = (side * side) / N
    
    print(f"Physics Result N={N}: Side={side:.6f}, Score={score:.6f}", file=sys.stderr)

    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python physics_packer.py <N>")
        sys.exit(1)
        
    N = int(sys.argv[1])
    try:
        res = run_simulation(N, steps=5000) # Increased steps for better settling
        
        # Output csv format
        print("id,x,y,deg")
        for i, r in enumerate(res):
            print(f"{N}_{i},s{r['x']},s{r['y']},s{r['deg']}")
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
