import dash
import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html
from dash.dependencies import Input, Output

# Read the data
df = pd.read_csv("data/arrival_rates.csv")

# Initialize the app
app = dash.Dash(__name__)

# Layout the design
app.layout = html.Div(
    [
        html.H1("Arrival Rate Heatmap", style={"textAlign": "center"}),
        dcc.Checklist(
            id="weekday-checkbox",
            options=[{"label": "Weekday", "value": True}, {"label": "Weekend", "value": False}],
            value=[True],
            inline=True,
        ),
        dcc.Slider(
            id="hour-slider",
            min=0,
            max=23.75,
            step=0.25,
            value=0,
            marks={i: "{}".format(i) for i in range(0, 24, 1)},
        ),
        dcc.Graph(id="heatmap"),
    ]
)


# Define the callback to update graph
@app.callback(
    Output("heatmap", "figure"), [Input("weekday-checkbox", "value"), Input("hour-slider", "value")]
)
def update_heatmap(weekday, hour):
    is_weekday = weekday[0] if weekday else False
    hour_df = df[(df["weekday"] == is_weekday) & (df["hour"] == hour)]
    pivot_df = hour_df.pivot(index="origin_stop", columns="destination_stop", values="arrival_rate")
    fig = go.Figure(
        data=go.Heatmap(
            z=pivot_df.values, x=pivot_df.columns, y=pivot_df.index, colorscale="Viridis"
        )
    )
    fig.update_layout(title=f"Hour: {hour}, Weekday: {is_weekday}", xaxis_nticks=36)
    return fig


if __name__ == "__main__":
    app.run_server(debug=True)
