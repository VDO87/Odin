import dash
from dash import dcc, html
import plotly.graph_objs as go

# Registro simples de eventos para exibir no dashboard
log: list[str] = []

app = dash.Dash(__name__)

# Dados iniciais das estratégias
estrategias = ["RSI", "MACD"]
pesos_iniciais = {"RSI": 5, "MACD": 7}

app.layout = html.Div(
    id="body",
    children=[
        html.H1("Dashboard Odin Zero"),
        dcc.Graph(id="grafico_pesos", figure={}),
        dcc.Slider(
            id="rsi_slider",
            min=0,
            max=10,
            step=0.1,
            value=pesos_iniciais["RSI"],
            marks={i: str(i) for i in range(11)},
        ),
        html.Div(
            id="rsi_value",
            children=f"Peso RSI: {pesos_iniciais['RSI']}",
        ),
        dcc.Slider(
            id="macd_slider",
            min=0,
            max=10,
            step=0.1,
            value=pesos_iniciais["MACD"],
            marks={i: str(i) for i in range(11)},
        ),
        html.Div(
            id="macd_value",
            children=f"Peso MACD: {pesos_iniciais['MACD']}",
        ),
        html.Div(
            [
                html.H3("Logger"),
                dcc.Textarea(
                    id="logger",
                    value="\n".join(log),
                    style={"width": "100%", "height": 200},
                    readOnly=True,
                ),
            ]
        ),
        html.Div(
            [html.Button("Trocar para Tema Escuro", id="toggle-theme", n_clicks=0)],
            style={"margin-top": "20px"},
        ),
    ],
)


@app.callback(
    dash.dependencies.Output("grafico_pesos", "figure"),
    [
        dash.dependencies.Input("rsi_slider", "value"),
        dash.dependencies.Input("macd_slider", "value"),
    ],
)
def update_graph(rsi_value: float, macd_value: float) -> dict:
    log.append(f"Slider Atualizado: RSI={rsi_value}, MACD={macd_value}")
    return {
        "data": [
            go.Bar(
                x=estrategias,
                y=[rsi_value, macd_value],
                name="Pesos",
                marker={"color": "rgba(58, 71, 80, 0.6)"},
            )
        ],
        "layout": go.Layout(
            title="Pesos das Estratégias",
            xaxis={"title": "Estratégias"},
            yaxis={"title": "Peso"},
        ),
    }


@app.callback(
    dash.dependencies.Output("rsi_value", "children"),
    dash.dependencies.Output("macd_value", "children"),
    dash.dependencies.Output("logger", "value"),
    [
        dash.dependencies.Input("rsi_slider", "value"),
        dash.dependencies.Input("macd_slider", "value"),
    ],
)
def update_values(rsi_value: float, macd_value: float) -> tuple[str, str, str]:
    log.append(f"Valor Ajustado: RSI={rsi_value}, MACD={macd_value}")
    return (
        f"Peso RSI: {rsi_value}",
        f"Peso MACD: {macd_value}",
        "\n".join(log),
    )


# Tema claro ou escuro
@app.callback(
    dash.dependencies.Output("body", "style"),
    dash.dependencies.Output("toggle-theme", "children"),
    [dash.dependencies.Input("toggle-theme", "n_clicks")],
)
def toggle_theme(n_clicks: int) -> tuple[dict, str]:
    if n_clicks % 2 == 0:
        return {"backgroundColor": "white", "color": "black"}, "Trocar para Tema Escuro"
    return {"backgroundColor": "black", "color": "white"}, "Trocar para Tema Claro"


if __name__ == "__main__":
    app.run_server(debug=True)
