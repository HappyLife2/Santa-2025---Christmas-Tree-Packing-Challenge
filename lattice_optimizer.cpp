#include <algorithm>
#include <cmath>
#include <ctime>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <random>
#include <vector>

// Use standard math constants
#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

using namespace std;

// --- GEOMETRY DEFINITIONS ---
constexpr int NV = 15;
// Exact coordinates from extracting_geometry.py / user code
const double TX[NV] = {0,     0.125, 0.0625, 0.2,     0.1,
                       0.35,  0.075, 0.075,  -0.075,  -0.075,
                       -0.35, -0.1,  -0.2,   -0.0625, -0.125};
const double TY[NV] = {0.8,  0.5, 0.5, 0.25, 0.25, 0,   0,  -0.2,
                       -0.2, 0,   0,   0.25, 0.25, 0.5, 0.5};

struct Point {
  double x, y;
};

struct Config {
  double x, y, deg;
};

// Rotate a point (px, py) by angle (radians)
Point rotate_pt(double px, double py, double angle) {
  double c = cos(angle);
  double s = sin(angle);
  return {px * c - py * s, px * s + py * c};
}

// Get global vertices for a configuration
vector<Point> get_vertices(const Config &c) {
  vector<Point> pts(NV);
  double rad = c.deg * M_PI / 180.0;
  double co = cos(rad), si = sin(rad);
  for (int i = 0; i < NV; ++i) {
    pts[i] = {c.x + TX[i] * co - TY[i] * si, c.y + TX[i] * si + TY[i] * co};
  }
  return pts;
}

// SAT Overlap Check
bool check_overlap(const vector<Point> &A, const vector<Point> &B) {
  auto is_sep = [&](const vector<Point> &P1, const vector<Point> &P2) {
    for (size_t i = 0; i < P1.size(); ++i) {
      size_t j = (i + 1) % P1.size();
      double ny = P1[i].x - P1[j].x;
      double nx = P1[j].y - P1[i].y;
      // Axis (nx, ny)
      double min1 = 1e9, max1 = -1e9;
      for (auto &p : P1) {
        double proj = nx * p.x + ny * p.y;
        min1 = min(min1, proj);
        max1 = max(max1, proj);
      }
      double min2 = 1e9, max2 = -1e9;
      for (auto &p : P2) {
        double proj = nx * p.x + ny * p.y;
        min2 = min(min2, proj);
        max2 = max(max2, proj);
      }
      if (max1 < min2 || max2 < min1)
        return true;
    }
    return false;
  };
  if (is_sep(A, B))
    return false;
  if (is_sep(B, A))
    return false;
  return true; // Overlap
}

// Calculate Area of Bounding Box
double calc_area(const vector<Config> &configs) {
  double min_x = 1e9, max_x = -1e9, min_y = 1e9, max_y = -1e9;
  for (const auto &c : configs) {
    vector<Point> pts = get_vertices(c);
    for (auto &p : pts) {
      min_x = min(min_x, p.x);
      max_x = max(max_x, p.x);
      min_y = min(min_y, p.y);
      max_y = max(max_y, p.y);
    }
  }
  return (max_x - min_x) * (max_y - min_y);
}

// Calculate bounds
struct Bounds {
  double min_x, max_x, min_y, max_y;
};
Bounds get_bounds(const vector<Config> &configs) {
  double min_x = 1e9, max_x = -1e9, min_y = 1e9, max_y = -1e9;
  for (const auto &c : configs) {
    vector<Point> pts = get_vertices(c);
    for (auto &p : pts) {
      min_x = min(min_x, p.x);
      max_x = max(max_x, p.x);
      min_y = min(min_y, p.y);
      max_y = max(max_y, p.y);
    }
  }
  return {min_x, max_x, min_y, max_y};
}

// --- OPTIMIZER ---
// Simulated Annealing for N=2 to minimize AREA
int main() {
  srand(time(0));

  // Setup N=2
  int n = 2;
  vector<Config> current(n);
  // Init random
  current[0] = {0, 0, 0};
  current[1] = {1.0, 0, 180}; // Initial guess

  double best_area = 1e9;
  vector<Config> best_config = current;

  // SA Params
  double T = 1.0;
  double cooling = 0.99999; // Slower cooling for finding the "Brick"
  double T_min = 1e-7;
  long long iter = 0;

  // Start loop
  while (T > T_min) {
    vector<Config> next = current;

    // Perturb
    int idx = rand() % n;
    int type = rand() % 2; // 0: Move, 1: Rotate

    if (type == 0) {
      next[idx].x += ((rand() % 1000) / 500.0 - 1.0) * T * 2.0;
      next[idx].y += ((rand() % 1000) / 500.0 - 1.0) * T * 2.0;
    } else {
      next[idx].deg += ((rand() % 1000) / 500.0 - 1.0) * T * 180.0;
    }

    // Normalize deg
    if (next[idx].deg > 360)
      next[idx].deg -= 360;
    if (next[idx].deg < 0)
      next[idx].deg += 360;

    // Check Overlap
    vector<Point> p0 = get_vertices(next[0]);
    vector<Point> p1 = get_vertices(next[1]);
    if (check_overlap(p0, p1)) {
      continue;
    }

    // Calculate Energy (Area)
    double area = calc_area(next);

    // Metropolis
    double diff = area - calc_area(current);

    if (diff < 0 || (exp(-diff / T) > (rand() / (double)RAND_MAX))) {
      current = next;
      if (area < best_area) {
        best_area = area;
        best_config = next;
        if (iter % 10000 == 0) {
          cout << "Iter " << iter << " T=" << fixed << setprecision(6) << T
               << " Area=" << best_area << "\r" << flush;
        }
      }
    }

    T *= cooling;
    iter++;
  }

  // Output Result
  Bounds b = get_bounds(best_config);
  double w = b.max_x - b.min_x;
  double h = b.max_y - b.min_y;

  cout << "\nFinal Best Area: " << best_area << endl;
  cout << "Dims: W=" << w << " H=" << h << endl;
  cout << "Efficiency: " << (best_area / 2.0) << " per tree" << endl;

  // Save to CSV for Python to pick up
  ofstream out("best_dimer.csv");
  out << "id,x,y,deg" << endl;
  for (int i = 0; i < n; ++i) {
    out << i << "," << best_config[i].x << "," << best_config[i].y << ","
        << best_config[i].deg << endl;
  }
  out.close();

  return 0;
}
