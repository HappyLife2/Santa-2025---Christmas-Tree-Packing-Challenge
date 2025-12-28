import cv2
import numpy as np
import matplotlib.pyplot as plt
from shapely.geometry import Polygon

def extract_tree_polygon(image_path):
    # Load image
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not load image {image_path}")
        return

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Threshold to get binary image (assuming dark tree on light background or vice versa)
    # Let's check the histogram or just use Otsu's
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        print("No contours found.")
        return

    # Assume the largest contour is the tree
    c = max(contours, key=cv2.contourArea)
    
    # Approximate the contour to reduce vertices (Douglas-Peucker algorithm)
    epsilon = 0.005 * cv2.arcLength(c, True)
    approx = cv2.approxPolyDP(c, epsilon, True)
    
    # Normalize coordinates
    # Center the tree at (0,0) based on bottom center or centroid?
    # Challenge says "point is defined at the center of the top of the trunk".
    # We need to manually identify this point or infer it. 
    # Usually trees are symmetric. Let's find the bounding box bottom center.
    
    pts = approx.reshape(-1, 2)
    min_x, min_y = np.min(pts, axis=0)
    max_x, max_y = np.max(pts, axis=0)
    
    # Coordinate system: standard image coords have y going down. 
    # Plotting usually has y going up.
    # Let's flip y first to match standard cartesian where y+ is up.
    pts[:, 1] = -pts[:, 1]
    
    # Re-calculate bounds after flip
    min_x, min_y = np.min(pts, axis=0)
    max_x, max_y = np.max(pts, axis=0)
    
    width = max_x - min_x
    height = max_y - min_y
    
    # Scale to typical unit size (maybe height=1 or similar? challenge doesn't specify scale, it's relative)
    # But let's keep aspect ratio.
    scale_factor = 1.0 / height
    pts = pts * scale_factor
    
    # Recenter
    # "center of the top of the trunk". 
    # This is hard to find automatically without heuristics.
    # Heuristic: The trunk is usually the lowest narrow part.
    # Let's just center x at 0 and put the bottom at y=0 for now, 
    # then we can adjust if we see the "trunk top" in the plot.
    
    center_x = (np.min(pts[:, 0]) + np.max(pts[:, 0])) / 2
    bottom_y = np.min(pts[:, 1])
    
    pts[:, 0] -= center_x
    pts[:, 1] -= bottom_y
    
    print(f"Extracted {len(pts)} vertices.")
    print("Vertices:", pts.tolist())
    
    # Plot to verify
    poly = Polygon(pts)
    x, y = poly.exterior.xy
    plt.figure()
    plt.plot(x, y)
    plt.scatter([0], [0], c='r', label='Origin (0,0)')
    plt.axis('equal')
    plt.legend()
    plt.savefig("extracted_tree.png")
    print("Saved extraction visualization to extracted_tree.png")

if __name__ == "__main__":
    image_path = "repo_data/inbox_8939556_f84b88f18d9ee1657b7229ad9fab9713_Gemini_Generated_Image_kgcl4gkgcl4gkgcl.png"
    extract_tree_polygon(image_path)
