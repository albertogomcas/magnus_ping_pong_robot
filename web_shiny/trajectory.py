import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp

import matplotlib
matplotlib.use('TkAgg')

# Constants
g = 9.81  # Gravity (m/s^2)
rho = 1.29  # Air density (kg/m^3)
C_d = 0.405  # Drag coefficient (for a sphere)
C_l = 0.62  # Lift coefficient (Magnus effect)
r = 0.020  # Radius of ball (m)
m = 0.00275  # Mass of ball (kg)
A = np.pi * r ** 2  # Cross-sectional area (m^2)
omega = np.array([0, -150, 300])  # Spin vector (rad/s)

# Initial conditions (position and velocity)
initial_conditions = [0, 0, 0.25, 10, 0, 0.5]  # [x, y, z, vx, vy, vz]

TABLE_LENGTH = 2.74  # meters
TABLE_WIDTH = 1.525  # meters
NET_HEIGHT = 0.1525  # meters


# Magnus force function
def magnus_force(v, omega):
    return 0.5 * C_l * rho * A * r * np.cross(omega, v)


# Equations of motion
def equations(t, y):
    x, y, z, vx, vy, vz = y
    v = np.array([vx, vy, vz])
    v_mag = np.linalg.norm(v)

    if v_mag == 0:
        drag = np.array([0, 0, 0])
        magnus = np.array([0, 0, 0])
    else:
        drag = -0.5 * rho * C_d * A * v_mag * v / m # Air resistance
        magnus = magnus_force(v, omega) / m  # Magnus force

    ax, ay, az = drag + magnus + np.array([0, 0, -g])

    return [vx, vy, vz, ax, ay, az]




time_span = (0, 5)  # Time span (0 to 5 seconds)
time_eval = np.linspace(0, 5, 500)  # Time points for solution

# Solve the equations of motion
solution = solve_ivp(equations, time_span, initial_conditions, t_eval=time_eval, method='RK45')

# Extract results
x_vals, y_vals, z_vals = solution.y[0], solution.y[1], solution.y[2]

valid_indices = z_vals > 0
x_vals, y_vals, z_vals = x_vals[valid_indices], y_vals[valid_indices], z_vals[valid_indices]


# Plot trajectory
fig = plt.figure(figsize=(16, 5))
ax1 = fig.add_subplot(131, projection='3d')
ax1.plot(x_vals, y_vals, z_vals, color="orange", lw=8)
ax1.set_xlabel("")
ax1.xaxis.line.set_color((1.0, 1.0, 1.0, 0.0))  # Hide X-axis line
ax1.yaxis.line.set_color((1.0, 1.0, 1.0, 0.0))  # Hide Y-axis line
ax1.zaxis.line.set_color((1.0, 1.0, 1.0, 0.0))  # Hide Z-axis line
ax1.set_xticks([])  # Remove X-axis ticks
ax1.set_yticks([])  # Remove Y-axis ticks
ax1.set_zticks([])  # Remove Z-axis ticks
ax1.grid(False)
ax1.xaxis.pane.fill = False
ax1.yaxis.pane.fill = False
ax1.zaxis.pane.fill = False

ax1.set_ylabel("")
ax1.set_zlabel("")
ax1.set_title("Spinning Ball Trajectory")

x_table = np.array([0, TABLE_LENGTH, TABLE_LENGTH, 0, 0])
y_table = np.array([-TABLE_WIDTH / 2, -TABLE_WIDTH / 2, TABLE_WIDTH / 2, TABLE_WIDTH / 2, -TABLE_WIDTH / 2])
z_table = np.zeros_like(x_table)
ax1.plot_trisurf(x_table, y_table, z_table, color='gray', alpha=0.5)

x_net = np.array([TABLE_LENGTH / 2, TABLE_LENGTH / 2, TABLE_LENGTH / 2, TABLE_LENGTH / 2])
y_net = np.array([-TABLE_WIDTH / 2, TABLE_WIDTH / 2, -TABLE_WIDTH / 2, TABLE_WIDTH / 2])
z_net = np.array([0, 0, NET_HEIGHT, NET_HEIGHT])

# Triangular faces
triangles_net = np.array([
    [0, 1, 2],  # First triangle
    [1, 2, 3]   # Second triangle
])
ax1.plot_trisurf(x_net, y_net, z_net, triangles=triangles_net, color='red', alpha=0.5)

ax1.set_box_aspect([TABLE_LENGTH, TABLE_WIDTH, NET_HEIGHT * 4])  # Ensure similar scale for axes

# Side View (X-Z plane)
ax2 = fig.add_subplot(132)

ax2.plot((0, TABLE_LENGTH), (0, 0), color='black', linestyle='-', lw=10)  # Table surface
ax2.plot((TABLE_LENGTH / 2, TABLE_LENGTH/2), (0, NET_HEIGHT), color='red', linestyle='-', lw=3)  # Net position

for spine in ax2.spines.values():
    spine.set_visible(False)
ax2.plot(x_vals, z_vals, color="orange", lw=8)
ax2.set_xlabel("")
ax2.set_ylabel("")
ax2.set_xticks([])
ax2.set_yticks([])
ax2.set_title("Side View (X-Z)")
ax2.set(
    xlim=(-0.1, TABLE_LENGTH+0.1),
    ylim=(-0.1, 0.5),
)
ax2.set_aspect('equal')

# Top View (X-Y plane)
ax3 = fig.add_subplot(133)

#Table outline
ax3.plot((0, 0), (-TABLE_WIDTH / 2, TABLE_WIDTH / 2), color='blue', linestyle='-', lw=3)  #
ax3.plot((TABLE_LENGTH, TABLE_LENGTH), (-TABLE_WIDTH / 2, TABLE_WIDTH / 2),  color='blue', linestyle='-', lw=3)
ax3.plot((0, TABLE_LENGTH), (0, 0),  color='blue', linestyle='-', lw=1)
ax3.plot((0, TABLE_LENGTH), (-TABLE_WIDTH / 2, -TABLE_WIDTH / 2),  color='blue', linestyle='-', lw=3)
ax3.plot((0, TABLE_LENGTH), (TABLE_WIDTH / 2, TABLE_WIDTH / 2),  color='blue', linestyle='-', lw=3)
ax3.plot((TABLE_LENGTH/2, TABLE_LENGTH/2), (-TABLE_WIDTH/2, TABLE_WIDTH/2), color='red', linestyle='-', lw=3)
ax3.fill_between((0, TABLE_LENGTH), (-TABLE_WIDTH / 2, -TABLE_WIDTH / 2), (TABLE_WIDTH / 2, TABLE_WIDTH / 2), color="gray")

ax3.plot(x_vals, y_vals, color="orange", lw=8, alpha=0.75)
for spine in ax3.spines.values():
    spine.set_visible(False)
ax3.set_xlabel("")
ax3.set_ylabel("")
ax3.set_xticks([])
ax3.set_yticks([])
ax3.set_title("Top View (X-Y)")
ax3.set(xlim = [-0.1, TABLE_LENGTH+0.1])
ax3.set_aspect('equal')

plt.tight_layout()
plt.show()