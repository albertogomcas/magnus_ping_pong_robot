# app.py  ---------------------------------------------------------------
# Run with:  shiny run --reload app.py
import asyncio
from shiny import App, ui, reactive, render

# ── UI ── ----------------------------------------------------------------
app_ui = ui.page_navbar(
    ui.nav_panel(
        "Drill Home",
        ui.h2("Drill")
    ),

    ui.nav_panel(                                   # ← the “sub-page”
        "Drill",
        ui.h3("Drill runner"),

        ui.input_numeric(           "n_steps",  "Number of steps",   10, min=1),
        ui.input_task_button(       "btn_run",  "Start drill"),
        ui.input_action_button(     "btn_cancel", "Cancel", class_="btn-danger"),

        ui.output_text("task_status"),
        ui.output_text_verbatim("task_result")
    ),

    title="Extended-Task demo"
)

# ── Server ── ------------------------------------------------------------
def server(input, output, session):

    # 1️⃣  Define the slow computation ------------------------------------
    @ui.bind_task_button(button_id="btn_run")      # keep the button busy while it runs
    @reactive.extended_task                        # run in the background  :contentReference[oaicite:0]{index=0}
    async def long_task(n_steps: int) -> str:
        """Loop n_steps times, sleeping 1 s each step and updating a progress bar.
        Returns a multi-line log when finished.  (Runs in its own asyncio task.)"""
        with ui.Progress(min=0, max=n_steps) as p:                 # progress bar  :contentReference[oaicite:1]{index=1}
            lines: list[str] = []
            for i in range(1, n_steps + 1):
                await asyncio.sleep(1)             # your heavy work goes here
                lines.append(f"step {i}/{n_steps} done")
                p.set(i, message=f"Working ({i}/{n_steps})")
        return "\n".join(lines)

    # 2️⃣  Start the task when the button is clicked ----------------------
    @reactive.effect
    @reactive.event(input.btn_run, ignore_init=True)      # don’t fire on app load
    def _start():
        long_task(int(input.n_steps()))                   # same as long_task.invoke(...)

    # 3️⃣  Cancel if the user presses “Cancel” ----------------------------
    @reactive.effect
    @reactive.event(input.btn_cancel)
    def _cancel():
        long_task.cancel()

    # 4️⃣  Reactive outputs that watch the task ---------------------------
    @output
    @render.text
    def task_status():
        if not long_task.running() and not long_task.finished():
            return "Task has not started yet."
        return f"Task status: {long_task.status()}"

    @output
    @render.text
    def task_result():
        if long_task.finished():
            try:
                return long_task.result()
            except Exception as e:
                return f"(Error: {e})"
        return "(no result yet)"

    @reactive.effect
    def _():
        if input.main_tab() == "Long Task":
            print("Entered long task tab")

# ── App object ── --------------------------------------------------------




if __name__ == "__main__":
    from shiny import run_app
    app = App(app_ui, server)
    run_app('drill:app', reload=True, host="10.0.0.168", port=80)