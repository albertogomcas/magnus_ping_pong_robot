# Web Magnus - Modular Structure

This directory contains the web interface for the RoboPong project, split into modular components for better maintainability.

## Structure

The application has been split into the following modules:

- `app.py` - Main application file that integrates all components
- `common.py` - Common functions, variables, and styles used across modules
- `control_panel.py` - Control panel UI and server logic
- `presets_panel.py` - Presets panel UI and server logic
- `target_panel.py` - Target panel UI and server logic
- `drill_panel.py` - Drill panel UI and server logic
- `calibrate_panel.py` - Calibrate panel UI and server logic
- `dev_panel.py` - Dev panel UI and server logic

## Running the Application

To run the application:

```bash
python app.py
```

This will start the Shiny server on the configured host and port.

## Development

Each panel is contained in its own file, making it easier to modify and extend functionality. To add a new panel:

1. Create a new file for your panel (e.g., `new_panel.py`)
2. Define the UI function (e.g., `ui_new_panel()`)
3. Define the server function (e.g., `server_new_panel()`)
4. Import and add your panel to `app.py`
