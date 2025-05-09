from shiny import App, ui, reactive
import matplotlib.pyplot as plt
from shiny import render
from trajectory import calculate

TABLE_LENGTH = 2.74  # meters
TABLE_WIDTH = 1.525  # meters
NET_HEIGHT = 0.1525  # meters

ratio = TABLE_WIDTH / TABLE_LENGTH

app_ui = ui.page_fluid(
ui.head_content(  # Add custom CSS to make the cursor visible
        ui.tags.style("""
            .shiny-plot-output:hover { 
                cursor: url('https://cur.cursors-4u.net/cursors/cur-1/cur5.cur'), crosshair;
            }
        """)
),
    ui.output_plot("plot", click=True, width="400px", height=f"{2*400*ratio:.0f}px"),
    ui.output_text("click_info"),  # Correct output for displaying text
    ui.input_slider("net_clearance", "Net Clearance", min=0, max=30, value=5, step=1),
    ui.input_slider("topspin", "Back<-----spin----->Top", min=-100, max=100, value=0, step=5),
    ui.input_slider("sidespin", "Left<\tspin\tRight", min=-100, max=100, value=0, step=5),
)

def plot_table():

    fig, ax = plt.subplots(figsize=(6, 2*6*ratio), nrows=2, sharex=True)
    ax[0].plot((0, 0), (-TABLE_WIDTH / 2, TABLE_WIDTH / 2), color='blue', linestyle='-', lw=3)  #
    ax[0].plot((TABLE_LENGTH, TABLE_LENGTH), (-TABLE_WIDTH / 2, TABLE_WIDTH / 2), color='blue', linestyle='-', lw=3)
    ax[0].plot((0, TABLE_LENGTH), (0, 0), color='blue', linestyle='-', lw=1)
    ax[0].plot((0, TABLE_LENGTH), (-TABLE_WIDTH / 2, -TABLE_WIDTH / 2), color='blue', linestyle='-', lw=3)
    ax[0].plot((0, TABLE_LENGTH), (TABLE_WIDTH / 2, TABLE_WIDTH / 2), color='blue', linestyle='-', lw=3)
    ax[0].plot((TABLE_LENGTH / 2, TABLE_LENGTH / 2), (-TABLE_WIDTH / 2, TABLE_WIDTH / 2), color='red', linestyle='-', lw=3)
    ax[0].fill_between((0, TABLE_LENGTH), (-TABLE_WIDTH / 2, -TABLE_WIDTH / 2), (TABLE_WIDTH / 2, TABLE_WIDTH / 2),
                     color="gray")


    for spine in ax[0].spines.values():
        spine.set_visible(False)
    ax[0].set_aspect('equal')
    ax[0].set_xticks([])
    ax[0].set_yticks([])

    ax[1].plot((0, TABLE_LENGTH), (0, 0), color='black', linestyle='-', lw=10)  # Table surface
    ax[1].plot((TABLE_LENGTH / 2, TABLE_LENGTH / 2), (0, NET_HEIGHT), color='red', linestyle='-', lw=3)  # Net position

    for spine in ax[1].spines.values():
        spine.set_visible(False)

    ax[1].set_aspect('equal')
    ax[1].set_xticks([])
    ax[1].set_yticks([])

    return fig, ax

def plot_trajectory(ax, x_vals, y_vals, z_vals):
    valid = z_vals > 0

    ax[0].plot(x_vals[valid], y_vals[valid], color="orange", lw=4, alpha=0.75)
    ax[1].plot(x_vals[valid], z_vals[valid], color="orange", lw=4, alpha=0.75)

def server(input, output, session):
    click_data = reactive.Value(None)
    @output
    @render.plot
    def plot():
        point = click_data.get()
        fig, ax = plot_table()

        if point is not None:
            x, y = point
            if x > TABLE_LENGTH / 2:
                net_clearance = input.net_clearance() / 100
                topspin = input.topspin()
                sidespin = input.sidespin()
                print(f"Solving for {x}, {y}m, clearance {net_clearance*100}cm, Tps{topspin}%, Sds{sidespin}%...")
                t_vals, x_vals, y_vals, z_vals = calculate(x, y, net_clearance=net_clearance, topspin=topspin, sidespin=sidespin)
                plot_trajectory(ax, x_vals, y_vals, z_vals)

        ax[0].set(
            xlim=[-0.1, TABLE_LENGTH+0.1],
            ylim=[-0.1-TABLE_WIDTH/2, TABLE_WIDTH/2 + 0.1],
        )
        ax[1].set(
            ylim=[-0.1, 0.5],
        )

        return fig

    @output
    @render.text
    def click_info():
        click = input.plot_click()
        if click:
            click_data.set((click["x"], click["y"]))
            return f"Clicked at: x={click['x']:.2f}, y={click['y']:.2f}"

app = App(app_ui, server)

if __name__ == "__main__":
    from shiny import run_app
    run_app('target:app', reload=True, host="10.0.0.168", port=80)