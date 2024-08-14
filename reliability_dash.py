import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.graph_objects as go
from dash.dependencies import Input, Output

# Read the CSV file
df = pd.read_csv("output_cleaned.csv")

# Define your list of stations
stations = [
    "Forest Park",
    "Cicero",
    "UIC_Halsted",
    "Clark/Lake",
    "Logan Square",
    "Jefferson Park",
    "O_Hare",
]

# Create a Dash app
app = dash.Dash(__name__)

# Define the app layout
app.layout = html.Div(
    [
        html.Div(
            [
                html.Div(
                    [
                        dcc.Dropdown(
                            id="dropdown1",
                            options=[
                                {"label": i, "value": i}
                                for i in df["block_type"].unique()
                            ],
                            value=df["block_type"].unique()[0],
                            placeholder="Select a signal system...",
                        ),
                        dcc.RadioItems(
                            id="radio1",
                            options=[
                                {"label": str(i), "value": i}
                                for i in df["which_slow_zones"].unique()
                            ],
                            value=df["which_slow_zones"].unique()[0],
                        ),
                        dcc.Dropdown(
                            id="dropdown3",
                            options=[
                                {"label": i, "value": i} for i in df["headway"].unique()
                            ],
                            value=df["headway"].unique()[0],
                            placeholder="Select mean headway...",
                        ),
                        dcc.Dropdown(
                            id="dropdown4",
                            options=[
                                {"label": i, "value": i}
                                for i in df["cv_headway"].unique()
                            ],
                            value=df["cv_headway"].unique()[0],
                            placeholder="Select CV headway...",
                        ),
                    ],
                    className="six columns",
                ),
                html.Div(
                    [
                        dcc.Dropdown(
                            id="dropdown5",
                            options=[
                                {"label": i, "value": i}
                                for i in df["block_type"].unique()
                            ],
                            value=df["block_type"].unique()[0],
                            placeholder="Select a signal system...",
                        ),
                        dcc.RadioItems(
                            id="radio2",
                            options=[
                                {"label": str(i), "value": i}
                                for i in df["which_slow_zones"].unique()
                            ],
                            value=df["which_slow_zones"].unique()[0],
                        ),
                        dcc.Dropdown(
                            id="dropdown7",
                            options=[
                                {"label": i, "value": i} for i in df["headway"].unique()
                            ],
                            value=df["headway"].unique()[0],
                            placeholder="Select mean headway...",
                        ),
                        dcc.Dropdown(
                            id="dropdown8",
                            options=[
                                {"label": i, "value": i}
                                for i in df["cv_headway"].unique()
                            ],
                            value=df["cv_headway"].unique()[0],
                            placeholder="Select CV headway...",
                        ),
                    ],
                    className="six columns",
                ),
            ],
            className="row",
        ),
        dcc.Graph(
            id="graph",
            config={
                "toImageButtonOptions": {
                    "format": "png",  # one of png, svg, jpeg, webp
                    "filename": "custom_image",
                    "height": 1600,
                    "width": 1600,
                    "scale": 6,  # Multiply title/legend/axis/canvas sizes by this factor
                }
            },
        ),
    ]
)


from plotly.subplots import make_subplots


@app.callback(
    Output("graph", "figure"),
    [
        Input("dropdown1", "value"),
        Input("radio1", "value"),
        Input("dropdown3", "value"),
        Input("dropdown5", "value"),
        Input("radio2", "value"),
        Input("dropdown7", "value"),
    ],
)
def update_graph(signal1, zone1, mean1, signal2, zone2, mean2):
    cv_headway_values = sorted(df["cv_headway"].unique())
    fig = make_subplots(rows=len(cv_headway_values), cols=1)

    for i, cv in enumerate(cv_headway_values, start=1):
        df_filtered1 = df[
            (df["block_type"] == signal1)
            & (df["which_slow_zones"] == zone1)
            & (df["headway"] == mean1)
            & (df["cv_headway"] == cv)
        ]

        df_filtered2 = df[
            (df["block_type"] == signal2)
            & (df["which_slow_zones"] == zone2)
            & (df["headway"] == mean2)
            & (df["cv_headway"] == cv)
        ]

        trace1_values = [
            df_filtered1[f"cv_headway_{station.replace(' ', '_')}"].mean()
            for station in stations
        ]

        trace2_values = [
            df_filtered2[f"cv_headway_{station.replace(' ', '_')}"].mean()
            for station in stations
        ]

        trace1 = go.Bar(
            x=[f"{stations[i]}" for i in range(len(stations))],
            y=trace1_values,
            name=(
                f"{signal1} {'with' if zone1 else 'without'} slow zones |  Average Dispatching"
                f" Headway of {mean1} (seconds)"
            ),
            legendgroup="group1",
            hovertemplate="<b>%{y}</b><extra></extra>",
            showlegend=i == 1,  # show legend only for the first subplot
            marker=dict(color="blue"),  # set color of bars
        )

        trace2 = go.Bar(
            x=[f"{stations[i]}" for i in range(len(stations))],
            y=trace2_values,
            name=(
                f"{signal2}  {'with' if zone2 else 'without'} slow zones | Average Dispatching"
                f" Headway of {mean2} (seconds)"
            ),
            legendgroup="group2",
            hovertemplate="<b>%{y}</b><extra></extra>",
            showlegend=i == 1,  # show legend only for the first subplot
            marker=dict(color="red"),  # set color of bars
        )

        fig.add_trace(trace1, row=i, col=1)
        fig.add_trace(trace2, row=i, col=1)

        fig.update_yaxes(title_text=f"CV Headway: {cv}", row=i, col=1)

    fig.update_layout(
        height=400
        * len(cv_headway_values),  # adjust height based on the number of subplots
        template="plotly_white",
        barmode="group",
        legend=dict(
            y=1.05,
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
        font=dict(family="Arial, sans-serif", size=14, color="black"),
    )

    return fig


# Run the app
if __name__ == "__main__":
    app.run_server(debug=True, port=8051)
