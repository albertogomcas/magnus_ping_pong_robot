import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp
from scipy.optimize import minimize, NonlinearConstraint, Bounds


import matplotlib
#matplotlib.use('TkAgg')

# Constants
g = 9.81  # Gravity (m/s^2)
rho = 1.29  # Air density (kg/m^3)
C_d = 0.405  # Drag coefficient (for a sphere)
C_l = 0.62  # Lift coefficient (Magnus effect)
r = 0.020  # Radius of ball (m)
m = 0.00275  # Mass of ball (kg)
A = np.pi * r ** 2  # Cross-sectional area (m^2)

Inertia = (2 / 3) * m * r**2 # hollow sphere moment of inertia

TABLE_LENGTH = 2.74  # meters
TABLE_WIDTH = 1.525  # meters
NET_HEIGHT = 0.1525  # meters
NET_X = TABLE_LENGTH / 2

TABLE_X_MIN = 0  # Starting edge of the table
TABLE_X_MAX = TABLE_LENGTH  # End of the table
TABLE_Y_MIN = -TABLE_WIDTH/2  # Half width (assuming center is y=0)
TABLE_Y_MAX = TABLE_WIDTH/2

ROBOT_HEAD_X = 0
ROBOT_HEAD_Y = 0
ROBOT_HEAD_Z = 0.3

v_max = 15  # Max initial speed (m/s)
max_rpm = 5000
omega_max = 0.10472 * max_rpm  # Max spin (rad/s)

reg_factor = 0.01

# Magnus force function
def magnus_force(v, omega):
    return 0.5 * C_l * rho * A * r * np.cross(omega, v)


# Equations of motion
def equations(t, y, omega):
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


def plot_trajectory(x_vals, y_vals, z_vals, target=None, landing=None):
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

    if target:
        ax2.plot(target[0], 0, "ro")
    if landing:
        ax2.plot(landing[0], 0, "bx")

    ax2.set_xlabel("")
    ax2.set_ylabel("")
    ax2.set_xticks([])
    ax2.set_yticks([])
    ax2.set_title("Side View (X-Z)")
    ax2.set(
        xlim=(-0.1, TABLE_LENGTH+0.1),
        ylim=(-0.1, 2),
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


    if target:
        ax3.plot(target[0], target[1], "ro")
    if landing:
        ax3.plot(landing[0], landing[1], "bx")

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

##

def solve_trajectory(initial_pos, initial_speed, omega, target=None):

    initial_conditions = initial_pos + initial_speed
    time_span = (0, 5)  # Time span (0 to 5 seconds)
    time_eval = np.linspace(0, 5, 500)  # Time points for solution

    # Solve the equations of motion
    solution = solve_ivp(equations, time_span, initial_conditions, t_eval=time_eval, method='RK45', args=(omega,))

    # Extract results
    t_vals, x_vals, y_vals, z_vals = solution.t, solution.y[0], solution.y[1], solution.y[2]

    valid_indices = z_vals > -0.1
    t_vals, x_vals, y_vals, z_vals = t_vals[valid_indices], x_vals[valid_indices], y_vals[valid_indices], z_vals[valid_indices]

    x_landing, y_landing = find_landing(t_vals, x_vals, y_vals, z_vals)

    #plot_trajectory(x_vals, y_vals, z_vals, target=target, landing=(x_landing, y_landing))



def simulate_trajectory(vx0, vy0, vz0, omega_x, omega_y, omega_z):
    initial_conditions = [ROBOT_HEAD_X, ROBOT_HEAD_Y, ROBOT_HEAD_Z, vx0, vy0, vz0]
    omega = np.array([omega_x, omega_y, omega_z])

    time_span = (0, 5)
    time_eval = np.linspace(0, 5, 500)

    sol = solve_ivp(equations, time_span, initial_conditions, t_eval=time_eval, method='RK45', args=(omega,))

    t_vals, x_vals, y_vals, z_vals = sol.t, sol.y[0], sol.y[1], sol.y[2]

    return t_vals, x_vals, y_vals, z_vals

def find_landing(t_vals, x_vals, y_vals, z_vals):

    for i in range(len(z_vals) - 1):
        if z_vals[i] > 0 and z_vals[i + 1] <= 0:  # Ball crosses the table height
            # Interpolate landing position
            x1, x2 = x_vals[i], x_vals[i + 1]
            y1, y2 = y_vals[i], y_vals[i + 1]
            z1, z2 = z_vals[i], z_vals[i + 1]

            # Linear interpolation to estimate exact (x, y) at z = 0
            alpha = -z1 / (z2 - z1)
            x_landing = x1 + alpha * (x2 - x1)
            y_landing = y1 + alpha * (y2 - y1)
            break
    else: # no landing, extrapolate a simple parabolic drop
        dt = t_vals[-1] - t_vals[-2]
        vx0 = (x_vals[-1] - x_vals[-2]) / dt
        vy0 = (y_vals[-1] - y_vals[-2]) / dt
        vz0 = (z_vals[-1] - z_vals[-2]) / dt
        z0 = z_vals[-1]

        t = 0
        while t < 10:
            z = z0 + vz0 * t - 0.5 * g * t**2
            if z <=0:
                break
            t += 0.1

        x_landing = x_vals[-1] + vx0 * t
        y_landing = y_vals[-1] + vy0 * t

    return x_landing, y_landing



def simplified_error_function(params, target_x, target_y, net_clearance):
    """Solve the problem with flatspin"""
    vx0, vy0, vz0, = params
    t_vals, x_vals, y_vals, z_vals = simulate_trajectory(vx0, vy0, vz0, 0, 0, 0)
    x_landing, y_landing = find_landing(t_vals, x_vals, y_vals, z_vals)
    # Compute squared error
    trajectory_error = (x_landing - target_x) ** 2 + (y_landing - target_y) ** 2
    znet_clearance = z_vals[np.argmin(np.abs(x_vals - TABLE_LENGTH / 2))] - NET_HEIGHT
    if znet_clearance < 0:
        net_penalty = 1000
    else:
        net_penalty = (znet_clearance - net_clearance) ** 2

    return trajectory_error + net_penalty


def error_function(params, target_x, target_y, net_clearance, target_topspin, target_sidespin):
    vx0, vy0, vz0, omega_x, omega_y, omega_z = params
    t_vals, x_vals, y_vals, z_vals = simulate_trajectory(vx0, vy0, vz0, omega_x, omega_y, omega_z)
    x_landing, y_landing = find_landing(t_vals, x_vals, y_vals, z_vals)

    # Energy penalty for high speed
    speed_penalty = reg_factor * 0.5 * m * (vx0**2 + vy0**2 + vz0**2)

    #Penalty for deviating from intended spin

    spin_penalty = reg_factor * ((omega_y - target_topspin)**2 + (omega_x-target_sidespin)**2)

    #penalty for balls too far from the intended net height
    znet_clearance = z_vals[np.argmin(np.abs(x_vals - TABLE_LENGTH/2))] - NET_HEIGHT
    if znet_clearance < 0:
        net_penalty = 1000
    else:
        net_penalty = (znet_clearance - net_clearance) ** 2

    # Compute squared error
    trajectory_error = (x_landing - target_x) ** 2 + (y_landing - target_y) ** 2

    #print(f"{trajectory_error=} {speed_penalty=} {spin_penalty=} {net_penalty=}")

    return trajectory_error + speed_penalty + spin_penalty + net_penalty

# Set bounds on velocity and spin
bounds = Bounds(
    [-v_max, -v_max, -v_max, -omega_max, -omega_max, -omega_max],  # Min values
    [v_max, v_max, v_max, omega_max, omega_max, omega_max]  # Max values
)


target_x = TABLE_LENGTH - 0.2  # Just before the table end
target_y = 0.1
target_z = 0  # Should land on the table

net_clearance = 0.1
target_topspin = -200
target_sidespin = 0


def calculate(target_x, target_y, net_clearance, topspin, sidespin):

    initial_nospin = tuple(minimize(simplified_error_function, (20, 0, 5), method="SLSQP", args=(target_x, target_y, net_clearance)).x)

    print(f"Initial nospin {initial_nospin} m/s")

    #solve_trajectory(initial_pos=(ROBOT_HEAD_X, ROBOT_HEAD_Y, ROBOT_HEAD_Z),
    #                 initial_speed=initial_nospin,
    #                 omega=(0,0,0),
    #                 target=(target_x, target_y)
    #                 )

    initial_guess = initial_nospin + (0, 0, 0)

    result = minimize(error_function, initial_guess, method='SLSQP', bounds=bounds, args=(target_x, target_y, net_clearance, omega_max*topspin/100, omega_max*sidespin/100))

    # Extract optimized values
    optimized_vx0, optimized_vy0, optimized_vz0, optimized_omega_x, optimized_omega_y, optimized_omega_z = result.x
    print(f"Optimized Initial Velocity: vx={optimized_vx0:.2f}, vy={optimized_vy0:.2f}, vz={optimized_vz0:.2f}")
    print(f"Optimized Spin: omega_x={optimized_omega_x:.2f}, omega_y={optimized_omega_y:.2f}, omega_z={optimized_omega_z:.2f}")

    return simulate_trajectory(optimized_vx0, optimized_vy0, optimized_vz0, optimized_omega_x, optimized_omega_y, optimized_omega_z)

    #solve_trajectory(initial_pos=(ROBOT_HEAD_X, ROBOT_HEAD_Y, ROBOT_HEAD_Z),
    #                 initial_speed=(optimized_vx0, optimized_vy0, optimized_vz0),
    #                 omega=(optimized_omega_x, optimized_omega_y, optimized_omega_z),
    #                 target=(target_x, target_y, target_z),
    #                 )