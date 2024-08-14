import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.graph_objects as go
import plotly.subplots as sp
from dash.dependencies import Input, Output

# Read the CSV file
df = pd.read_csv("output_slow_zones.csv")

# Convert any NaN values to string 'None' for dropdown compatibility
df = df.fillna("None")
df["offscan_symptomatic_block_index"] = df["offscan_symptomatic_block_index"].astype(
    str
)

# For dropping entries based on the condition
df = df[df["avg_headway_Forest_Park"] >= 100]

df.dropna(inplace=True)

# Create a Dash app
app = dash.Dash(__name__)

# First column layout
column_1 = html.Div(
    [
        dcc.Dropdown(
            id="block_type_dropdown",
            options=[
                {"label": str(i), "value": str(i)}
                for i in sorted(df["block_type"].unique())
            ],
            value=str(df["block_type"].unique()[0]),
            placeholder="Select Block Type",
        ),
        dcc.Dropdown(
            id="offscan_symptomatic_block_index_dropdown",
            options=[
                {"label": str(i), "value": str(i)}
                for i in sorted(df["offscan_symptomatic_block_index"].unique())
            ],
            value=str(df["offscan_symptomatic_block_index"].unique()[0]),
            placeholder="Enter offscan_symptomatic_block_index",
        ),
        dcc.Dropdown(
            id="offscan_probability_dropdown",
            options=[
                {"label": str(i), "value": str(i)}
                for i in sorted(df["offscan_probability"].unique())
            ],
            value=str(df["offscan_probability"].unique()[0]),
            placeholder="Enter offscan_probability",
        ),
        dcc.Graph(
            id="graph_1",
            config={
                "toImageButtonOptions": {
                    "format": "png",
                    "filename": "custom_image",
                    "height": 300 * 4,
                    "width": 800,
                    "scale": 6,
                }
            },
        ),
    ],
    style={"width": "48%", "display": "inline-block", "vertical-align": "top"},
)

# Second column layout
column_2 = html.Div(
    [
        dcc.Dropdown(
            id="block_type_dropdown_2",
            options=[
                {"label": str(i), "value": str(i)}
                for i in sorted(df["block_type"].unique())
            ],
            value=str(df["block_type"].unique()[0]),
            placeholder="Select Block Type",
        ),
        dcc.Dropdown(
            id="offscan_symptomatic_block_index_dropdown_2",
            options=[
                {"label": str(i), "value": str(i)}
                for i in sorted(df["offscan_symptomatic_block_index"].unique())
            ],
            value=str(df["offscan_symptomatic_block_index"].unique()[0]),
            placeholder="Enter offscan_symptomatic_block_index",
        ),
        dcc.Dropdown(
            id="offscan_probability_dropdown_2",
            options=[
                {"label": str(i), "value": str(i)}
                for i in sorted(df["offscan_probability"].unique())
            ],
            value=str(df["offscan_probability"].unique()[0]),
            placeholder="Enter offscan_probability",
        ),
        dcc.Graph(
            id="graph_2",
            config={
                "toImageButtonOptions": {
                    "format": "png",
                    "filename": "custom_image_2",
                    "height": 300 * 4,
                    "width": 800,
                    "scale": 6,
                }
            },
        ),
    ],
    style={
        "width": "48%",
        "display": "inline-block",
        "vertical-align": "top",
        "margin-left": "4%",
    },
)

# App layout
app.layout = html.Div([column_1, column_2])


# Callback for the first graph
@app.callback(
    Output("graph_1", "figure"),
    [
        Input("block_type_dropdown", "value"),
        Input("offscan_symptomatic_block_index_dropdown", "value"),
        Input("offscan_probability_dropdown", "value"),
    ],
)
def update_graph(block_type, offscan_symptomatic_block_index, offscan_probability):
    df_filtered = df[
        (df["block_type"] == block_type)
        & (
            df["offscan_symptomatic_block_index"]
            == str(offscan_symptomatic_block_index)
        )
        # & (df["offscan_probability"] == float(offscan_probability))
    ]

    cv_headway_values = sorted(df_filtered["cv_headway"].unique())
    fig = sp.make_subplots(rows=len(cv_headway_values), cols=1)

    color_map = {
        "Current": "red",
        "None": "blue",
        "Uniform": "purple",
        # Add any other colors and map them to the appropriate slow_zones values if necessary.
    }

    for i, cv_headway in enumerate(cv_headway_values, start=1):
        df_sub = df_filtered[df_filtered["cv_headway"] == cv_headway]

        for zone in df_sub["which_slow_zones"].unique():
            df_zone = df_sub[df_sub["which_slow_zones"] == zone]

            # Sort the dataframe based on the x-values before plotting
            df_zone = df_zone.sort_values(by="avg_headway_Forest_Park")

            trace = go.Scatter(
                x=df_zone["avg_headway_Forest_Park"],
                y=df_zone["avg_travel_time"],
                mode="lines",
                name=f"{zone}",
                legendgroup=f"{zone}",
                line=dict(color=color_map[zone]),
                showlegend=(i == 1),  # Show legend only for the first subplot
            )
            fig.add_trace(trace, row=i, col=1)

        # Update y-axis title for this subplot
        fig.update_yaxes(title_text=f"CV Headway: {cv_headway}", row=i, col=1)

    fig.update_layout(
        title=dict(
            text="Running Time vs Dispatching Headway",
            y=0.99,
            x=0.5,
            xanchor="center",
            yanchor="top",
        ),
        legend=dict(
            title="Slow Zones",
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
        template="plotly_white",
        font=dict(
            family="Arial, sans-serif",
            size=14,
            color="black",
        ),
        autosize=False,
        width=800,
        height=500 * len(cv_headway_values),
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
        title_text="Average Dispatching Headway (seconds)",
        row=len(cv_headway_values),
        col=1,
    )

    # Update graph aesthetics for finer grid
    fig.update_layout(
        xaxis=dict(gridcolor="lightgray", gridwidth=0.5),
        yaxis=dict(gridcolor="lightgray", gridwidth=0.5),
    )

    for i in range(1, len(cv_headway_values) + 1):
        fig.update_xaxes(
            gridcolor="lightgray", gridwidth=0.5, range=[80, 370], row=i, col=1
        )
        fig.update_yaxes(
            gridcolor="lightgray", gridwidth=0.5, range=[55, 90], row=i, col=1
        )

    fig.update_xaxes(range=[80, 370])  # Set x-axis limits to 150-370
    fig.update_yaxes(range=[60, 90])  # Set y-axis limits to 80-90

    return fig


# Callback for the second graph
@app.callback(
    Output("graph_2", "figure"),
    [
        Input("block_type_dropdown_2", "value"),
        Input("offscan_symptomatic_block_index_dropdown_2", "value"),
        Input("offscan_probability_dropdown_2", "value"),
    ],
)
def update_graph_2(block_type, offscan_symptomatic_block_index, offscan_probability):
    df_filtered = df[
        (df["block_type"] == block_type)
        & (
            df["offscan_symptomatic_block_index"]
            == str(offscan_symptomatic_block_index)
        )
        # & (df["offscan_probability"] == float(offscan_probability))
    ]

    cv_headway_values = sorted(df_filtered["cv_headway"].unique())
    fig = sp.make_subplots(rows=len(cv_headway_values), cols=1)

    color_map = {
        "Current": "red",
        "None": "blue",
        "Uniform": "purple",
        # Add any other colors and map them to the appropriate slow_zones values if necessary.
    }

    offscan_probability_colors = {
        0.0: "red",
        0.5: "blue",
        1.0: "green",
        # Add more probabilities and colors if needed.
    }

    for i, cv_headway in enumerate(cv_headway_values, start=1):
        df_sub = df_filtered[df_filtered["cv_headway"] == cv_headway]

        for prob in df_sub["offscan_probability"].unique():
            df_prob = df_sub[df_sub["offscan_probability"] == prob]

            # Sort the dataframe based on the x-values before plotting
            df_prob = df_prob.sort_values(by="avg_headway_Forest_Park")

            trace = go.Scatter(
                x=df_prob["avg_headway_Forest_Park"],
                y=df_prob["avg_travel_time"],
                mode="lines",
                name=f"Probability: {prob}",
                legendgroup=f"{prob}",
                line=dict(color=offscan_probability_colors[prob]),
                showlegend=(i == 1),  # Show legend only for the first subplot
            )
            fig.add_trace(trace, row=i, col=1)

        # Update y-axis title for this subplot
        fig.update_yaxes(title_text=f"CV Headway: {cv_headway}", row=i, col=1)

    fig.update_layout(
        title=dict(
            text="Running Time vs Dispatching Headway",
            y=0.99,
            x=0.5,
            xanchor="center",
            yanchor="top",
        ),
        legend=dict(
            title="Probability",
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
        template="plotly_white",
        font=dict(
            family="Arial, sans-serif",
            size=14,
            color="black",
        ),
        autosize=False,
        width=800,
        height=500 * len(cv_headway_values),
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
        title_text="Average Dispatching Headway (seconds)",
        row=len(cv_headway_values),
        col=1,
    )

    # Update graph aesthetics for finer grid
    fig.update_layout(
        xaxis=dict(gridcolor="lightgray", gridwidth=0.5),
        yaxis=dict(gridcolor="lightgray", gridwidth=0.5),
    )

    for i in range(1, len(cv_headway_values) + 1):
        fig.update_xaxes(
            gridcolor="lightgray", gridwidth=0.5, range=[150, 370], row=i, col=1
        )
        fig.update_yaxes(
            gridcolor="lightgray", gridwidth=0.5, range=[80, 85], row=i, col=1
        )

    fig.update_xaxes(range=[150, 370])  # Set x-axis limits to 150-370
    fig.update_yaxes(range=[80, 85])  # Set y-axis limits to 80-90

    return fig


# Run the app
if __name__ == "__main__":
    app.run_server(debug=True)
