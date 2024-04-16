import pandas as pd
import plotly.graph_objects as go
import plotly.subplots as sp
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

# Read the CSV file
df = pd.read_csv("output.csv")

# Create a Dash app
app = dash.Dash(__name__)

# Define the app layout
app.layout = html.Div(
    [
        dcc.Dropdown(
            id="dropdown",
            options=[{"label": i, "value": i} for i in df["cv_headway"].unique()],
            value=df["cv_headway"].unique()[0],
        ),
        dcc.Graph(
            id="graph",
            config={
                "toImageButtonOptions": {
                    "format": "png",  # one of png, svg, jpeg, webp
                    "filename": "custom_image",
                    "height": 300 * 4,
                    "width": 800,
                    "scale": 6,  # Multiply title/legend/axis/canvas sizes by this factor
                }
            },
        ),
    ]
)


def get_zone_name(slow_zones):
    if slow_zones == "True":
        return "with Current Slow Zones"
    elif slow_zones == "False":
        return "without Slow Zones"
    elif slow_zones == "uniform":
        return "with Uniform Slow Zones"
    else:
        raise ValueError(f"Unknown slow_zones value: {slow_zones}")


# Define the callback to update the graph
@app.callback(Output("graph", "figure"), [Input("dropdown", "value")])
def update_graph(cv_headway):
    # Filter dataframe for the current cv_headway
    cv_headway_values = sorted(df["cv_headway"].unique())

    # Create a figure with subplots
    fig = sp.make_subplots(rows=len(cv_headway_values), cols=1)

    color_dict = {
        "FixedBlock with Current Slow Zones": "red",
        "FixedBlock without Slow Zones": "blue",
        "FixedBlock with Uniform Slow Zones": "purple",
        "MovingBlock with Current Slow Zones": "green",
        "MovingBlock without Slow Zones": "orange",
        "MovingBlock with Uniform Slow Zones": "cyan",  # added this color
    }

    # For each unique cv_headway
    for i, cv_headway in enumerate(cv_headway_values, start=1):
        df_filtered_cv = df[df["cv_headway"] == cv_headway]

        # Create a dictionary that will hold our traces
        traces = {}

        # For each combination of signal system and slow zones
        for signal_system, slow_zones in (
            df_filtered_cv[["signal_system", "slow_zones"]].drop_duplicates().values
        ):
            # Filter dataframe for the current combination
            df_filtered = df_filtered_cv[
                (df_filtered_cv["signal_system"] == signal_system)
                & (df_filtered_cv["slow_zones"] == slow_zones)
            ].sort_values(by="avg_headway_Forest_Park")

            # Create a trace for this combination
            trace = go.Scatter(
                x=df_filtered["avg_headway_Forest_Park"],
                y=df_filtered["avg_travel_time"],
                mode="lines",
                name=f"{signal_system} {get_zone_name(slow_zones)}",  # modified this line
                legendgroup=f"{signal_system} {get_zone_name(slow_zones)}",  # and this line
                line=dict(
                    color=color_dict[
                        f"{signal_system} {get_zone_name(slow_zones)}"  # and this line
                    ]
                ),
                showlegend=(i == 1),  # Show legend only for the first subplot
            )

            # Add trace to the subplot for this cv_headway
            fig.add_trace(trace, row=i, col=1)

        # Update y-axis title for this subplot
        fig.update_yaxes(title_text=f"CV Headway: {cv_headway}", row=i, col=1)

    # Set labels and update layout for publication-quality
    fig.update_layout(
        title=dict(
            text="Running Time vs Dispatching Headway",
            y=0.99,
            x=0.5,
            xanchor="center",
            yanchor="top",
        ),
        legend=dict(
            y=1.06,
            x=0.5,
            xanchor="center",
            yanchor="top",
            traceorder="normal",
            font=dict(family="Arial, sans-serif", size=14, color="black"),
            bgcolor="White",
            bordercolor="Black",
            borderwidth=2,
            orientation="h",  # horizontal orientation
            itemsizing="constant",  # ensure the legend symbols have the same size
            itemwidth=50,  # width (in px) of legend items
            itemclick="toggleothers",  # only the clicked data series is displayed
        ),
        template="plotly_white",  # You can experiment with other templates like "plotly", "ggplot2", "seaborn", "simple_white"
        font=dict(
            family="Arial, sans-serif",  # You can change this to Times, Times New Roman, etc.
            size=14,
            color="black",
        ),
        autosize=False,
        width=800,  # You can adjust these sizes according to your needs
        height=500 * len(cv_headway_values),
        # Add annotation for pseudo-global y-axis title
        annotations=[
            dict(
                x=-0.075,
                y=0.5,
                showarrow=False,
                text="Average Running Time (minutes)",
                textangle=-90,
                xref="paper",
                yref="paper",
            )
        ],
    )

    # Update x-axis title only for the bottom subplot
    fig.update_xaxes(
        title_text="Average Dispatching Headway (seconds)", row=len(cv_headway_values), col=1
    )

    return fig


# Run the app
if __name__ == "__main__":
    app.run_server(debug=True)
