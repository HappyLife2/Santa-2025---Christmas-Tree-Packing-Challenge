#include <algorithm>
#include <cmath>
#include <ctime>
#include <iomanip>
#include <iostream>
#include <random>
#include <vector>

// Use standard math constants
#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

using namespace std;

constexpr int NV = 15;
// Exact coordinates
const double TX[NV] = {0,     0.125, 0.0625, 0.2,     0.1,
                       0.35,  0.075, 0.075,  -0.075,  -0.075,
                       -0.35, -0.1,  -0.2,   -0.0625, -0.125};
const double TY[NV] = {0.8,  0.5, 0.5, 0.25, 0.25, 0,   0,  -0.2,
                       -0.2, 0,   0,   0.25, 0.25, 0.5, 0.5};

// Robust Polygon Struct (from single_group_optimizer)
struct Poly {
  double px[NV], py[NV];
  double x0, y0, x1, y1; // AABB
};

inline void getPoly(double cx, double cy, double deg, Poly &q) {
  double rad = deg * (M_PI / 180.0);
  double s = sin(rad), c = cos(rad);
  double minx = 1e9, miny = 1e9, maxx = -1e9, maxy = -1e9;
  for (int i = 0; i < NV; i++) {
    double x = TX[i] * c - TY[i] * s + cx;
    double y = TX[i] * s + TY[i] * c + cy;
    q.px[i] = x;
    q.py[i] = y;
    if (x < minx)
      minx = x;
    if (x > maxx)
      maxx = x;
    if (y < miny)
      miny = y;
    if (y > maxy)
      maxy = y;
  }
  q.x0 = minx;
  q.y0 = miny;
  q.x1 = maxx;
  q.y1 = maxy;
}

inline bool pip(double px, double py, const Poly &q) {
  bool in = false;
  int j = NV - 1;
  for (int i = 0; i < NV; i++) {
    if ((q.py[i] > py) != (q.py[j] > py) &&
        px < (q.px[j] - q.px[i]) * (py - q.py[i]) / (q.py[j] - q.py[i]) +
                 q.px[i])
      in = !in;
    j = i;
  }
  return in;
}

inline bool segInt(double ax, double ay, double bx, double by, double cx,
                   double cy, double dx, double dy) {
  double d1 = (dx - cx) * (ay - cy) - (dy - cy) * (ax - cx);
  double d2 = (dx - cx) * (by - cy) - (dy - cy) * (bx - cx);
  double d3 = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax);
  double d4 = (bx - ax) * (dy - ay) - (by - ay) * (dx - ax);
  return ((d1 > 0) != (d2 > 0)) && ((d3 > 0) != (d4 > 0));
}

inline bool overlap(const Poly &a, const Poly &b) {
  if (a.x1 < b.x0 || b.x1 < a.x0 || a.y1 < b.y0 || b.y1 < a.y0)
    return false;
  for (int i = 0; i < NV; i++) {
    if (pip(a.px[i], a.py[i], b))
      return true;
    if (pip(b.px[i], b.py[i], a))
      return true;
  }
  for (int i = 0; i < NV; i++) {
    int ni = (i + 1) % NV;
    for (int j = 0; j < NV; j++) {
      int nj = (j + 1) % NV;
      if (segInt(a.px[i], a.py[i], a.px[ni], a.py[ni], b.px[j], b.py[j],
                 b.px[nj], b.py[nj]))
        return true;
    }
  }
  return false;
}

// Config Struct
struct Config {
  double x, y, deg;
};

// Canonical Lattice Check
// Basis: (a, 0), (b, c)
bool check_lattice_validity(const Config &t1, const Config &t2, double a,
                            double b, double c) {
  Poly p1, p2;
  getPoly(t1.x, t1.y, t1.deg, p1);
  getPoly(t2.x, t2.y, t2.deg, p2);

  if (overlap(p1, p2))
    return false;

  // Bounds check to avoid long slivers
  if (a > 5.0 || c > 5.0)
    return false;

  // Check Neighbors
  // Tree Size approx 1.0. Distance check 3.0 safe.
  // Range 3
  for (int i = -3; i <= 3; ++i) {
    for (int j = -3; j <= 3; ++j) {
      if (i == 0 && j == 0)
        continue;

      double dx = i * a + j * b;
      double dy = j * c;

      if (dx * dx + dy * dy > 9.0)
        continue;

      Poly p1_shift, p2_shift;

      // Shift T1
      p1_shift = p1;
      for (int k = 0; k < NV; ++k) {
        p1_shift.px[k] += dx;
        p1_shift.py[k] += dy;
      }
      p1_shift.x0 += dx;
      p1_shift.x1 += dx;
      p1_shift.y0 += dy;
      p1_shift.y1 += dy;

      if (overlap(p1, p1_shift))
        return false;

      // Shift T2
      p2_shift = p2;
      for (int k = 0; k < NV; ++k) {
        p2_shift.px[k] += dx;
        p2_shift.py[k] += dy;
      }
      p2_shift.x0 += dx;
      p2_shift.x1 += dx;
      p2_shift.y0 += dy;
      p2_shift.y1 += dy;

      if (overlap(p2, p2_shift))
        return false;

      // Cross check
      if (overlap(p1, p2_shift))
        return false;
      if (overlap(p2, p1_shift))
        return false;
    }
  }
  return true;
}

int main() {
  srand(time(0));

  double a = 1.0;
  double b = 0.0;
  double c = 1.0;

  Config t1 = {0, 0, 0};
  Config t2 = {0.5, 0.5, 180};

  double best_area = 1e9;

  // Multi-start SA
  for (int restart = 0; restart < 10; ++restart) {
    double T = 0.5;
    double cooling = 0.99995;

    while (T > 1e-6) {
      double n_a = a + ((rand() % 1000) / 500.0 - 1.0) * T * 0.5;
      if (n_a < 0.5)
        n_a = 0.5;

      double n_b = b + ((rand() % 1000) / 500.0 - 1.0) * T * 0.5;

      double n_c = c + ((rand() % 1000) / 500.0 - 1.0) * T * 0.5;
      if (n_c < 0.5)
        n_c = 0.5;

      Config n_t2 = t2;
      n_t2.x += ((rand() % 1000) / 500.0 - 1.0) * T;
      n_t2.y += ((rand() % 1000) / 500.0 - 1.0) * T;
      n_t2.deg += ((rand() % 1000) / 500.0 - 1.0) * T * 180.0;

      // Bound T2 to Unit Cell
      if (n_t2.x > 3.0)
        n_t2.x = 3.0;
      if (n_t2.x < -3.0)
        n_t2.x = -3.0;
      if (n_t2.y > 3.0)
        n_t2.y = 3.0;
      if (n_t2.y < -3.0)
        n_t2.y = -3.0;

      double area = n_a * n_c;

      if (check_lattice_validity(t1, n_t2, n_a, n_b, n_c)) {
        double diff = area - (a * c);
        if (diff < 0 || (exp(-diff / T) > (rand() / (double)RAND_MAX))) {
          a = n_a;
          b = n_b;
          c = n_c;
          t2 = n_t2;
          if (area < best_area) {
            best_area = area;
            cout << "\nNew Best R" << restart << " Area=" << best_area << endl;
            cout << "  Lat: a=" << a << " b=" << b << " c=" << c << endl;
            cout << "  T2: x=" << t2.x << " y=" << t2.y << " deg=" << t2.deg
                 << endl;
          }
        }
      }
      T *= cooling;
    }
    // Jolt
    a = 1.2;
    b = 0.0;
    c = 1.2;
    t2.x = ((rand() % 200) / 100.0);
    t2.y = ((rand() % 200) / 100.0);
    t2.deg = rand() % 360;
  }

  cout << "\n\nFinal Robust Area: " << best_area << endl;
  cout << "Vectors: (" << a << ",0), (" << b << "," << c << ")" << endl;
  cout << "Tree Density: " << (0.245625 * 2) / best_area << endl;

  return 0;
}
