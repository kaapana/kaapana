import os.path

import pandas as pd
from dash import Dash, html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
import argparse
import numpy as np
from typing import *
from datetime import datetime
import dash
try:
    from typing import TypedDict  # >=3.8
except ImportError:
    from mypy_extensions import TypedDict  # <=3.7
import base64
import io
import webbrowser
from pathlib import Path


from data_reader import DataReader


class Annotation(TypedDict):
    annotator: str
    time: datetime
    choice: int


class Annotations:
    def __init__(self):
        self.data_reader: Union[DataReader, None] = None
        self.data: Dict[str, Annotation] = {}
        self.user: Union[str, None] = None

    def format_data(self) -> pd.DataFrame:
        data_dict = dict(annotator=[],
                         time=[],
                         file=[],
                         choice=[],
                         )
        for key, value in self.data.items():
            data_dict["annotator"].append(value["annotator"])
            data_dict["time"].append(value["time"])
            data_dict["file"].append(key)
            data_dict["choice"].append(value["choice"])
        return pd.DataFrame(data_dict)

    def resume_annotation_from_csv(self, df) -> None:
        for i in range(len(df["file"])):
            self.data[df["file"][i]] = Annotation(annotator=df["annotator"][i],
                                                  time=df["time"][i],
                                                  choice=df["choice"][i])

    def get_unannotated_file_ids(self) -> list:
        unannotated_file_id_list = []
        for file_index in range(self.data_reader.n_images):
            data_path = self.data_reader.get_filename(selected_id=file_index)
            if data_path not in self.data:
                unannotated_file_id_list.append(file_index)

        return unannotated_file_id_list


EXTERNAL_STYLES = [dbc.themes.JOURNAL]
URL_BASE_PATH = os.getenv('INGRESS_PATH', None)
OPERATOR_OUT_DIR = os.getenv('OPERATOR_OUT_DIR',"")
flag_disabled = True if OPERATOR_OUT_DIR else False

if URL_BASE_PATH is not None:
    USER_ID = os.getenv("ANNOTATOR", "annotator")
    print("#####################")
    print("User id: ", USER_ID)
    print("#####################")
    RATEME_FOLDER = '/kaapana/mounted/rateme-data'
    invalid_flag = False
    valid_flag = True
    URL_BASE_PATH += '/'
    path_logo = f'{URL_BASE_PATH}assets/dkfz.png'
    prevent_initial_call = False
else:
    USER_ID = ""
    RATEME_FOLDER = ""
    path_logo = '/assets/dkfz.png'
    invalid_flag = True
    valid_flag = False
    prevent_initial_call = True
    
DATA = Annotations()
DATA.data = {}
TMP_DATA = {"path": None, "user": None}
app = Dash(__name__, external_stylesheets=EXTERNAL_STYLES, title="RateMe", url_base_pathname=URL_BASE_PATH)

app.layout = html.Div([
    html.Div(
        id='dummy_load',
        children=[],
        style={'display': 'none'}
    ),
    html.Div(
        id='dummy_buttons',
        children=[],
        style={'display': 'none'}
    ),
    html.Div(
        id='dummy_update',
        children=[],
        style={'display': 'none'}
    ),
    html.H1(
        className="bg-info text-white p-2",
        children=[
            dbc.Row([
                dbc.Col([
                    "RateMe"
                ], width={"size": 1, 'offset': 0}),
                dbc.Col([
                    html.Img(src=path_logo,
                             height='70px'),  # ToDo: x-ray size can vary
                ], width={'size': 1, 'offset': 9})
            ])
        ]
    ),
    dbc.Row([
        dbc.Col([
            dbc.InputGroup([
                dbc.InputGroupText(
                    "/",
                    className="bg-info text-white p-2"
                ),
                dbc.Input(
                    id="data_path",
                    type="text",
                    pattern=None,
                    placeholder="Set path to data folder",
                    persistence=True,
                    persistence_type="session",
                    style={'width': '75%', 'display': 'inline-block'},
                    invalid=invalid_flag,
                    valid=valid_flag,
                    autofocus=True,
                    debounce=True,
                    value=RATEME_FOLDER
                ),
            ]),
            html.Br(),
            dbc.InputGroup([
                dbc.InputGroupText(
                    "@",
                    className="bg-info text-white p-2"
                ),
                dbc.Input(
                    id="user",
                    type="text",
                    pattern=None,
                    placeholder="Set user ID",
                    persistence=True,
                    persistence_type="session",
                    style={'width': '75%', 'display': 'inline-block'},
                    debounce=True,
                    value=USER_ID,
                    valid=valid_flag,
                    invalid=invalid_flag
                ),
            ]),
            html.Br(),
            html.Br(),
            dcc.Upload(
                id="upload",
                children=html.Div([
                    'Drag and Drop or ',
                    html.A('Select .csv'),
                ]),
                style={
                    'width': '100%',
                    'height': '60px',
                    'lineHeight': '60px',
                    'borderWidth': '1px',
                    'borderStyle': 'dashed',
                    'borderRadius': '5px',
                    'textAlign': 'center',
                    'margin': '10px'
                },
                accept=".csv",
                disabled=True
            ),
            dbc.Popover([
                dbc.PopoverHeader("Upload .csv"),
                dbc.PopoverBody("Overwrites the current annotation labels")
            ], id="upload_csv_popover", target="upload", trigger="hover", placement="bottom"
            ),
            html.Br(),
            dbc.Button(
                "Download",
                id="download_button",
                style={'display': 'inline-block', 'verticalAlign': 'top', 'margin-left': '5px'},
                outline=True,
                color="info",
                disabled=True
            ),
            dcc.Download(
                id="download",
            ),
            dbc.Popover([
                dbc.PopoverHeader("Download annotations"),
                dbc.PopoverBody("Downloads the current annotation values as .csv file")
            ], id="download_annotations_popover", target="download_button", trigger="hover", placement="bottom"
            ),
            html.Br(),
            html.Br(),
            dbc.Card([
                dbc.CardHeader("About"),
                dbc.CardBody(
                    html.P(["1. Set path to data folder and user ID on the left.", html.Br(),
                            html.Br(),
                            "2. Annotate image selection by using the buttoms.", html.Br(),
                            #"A progressbar at the top indicates how many images were annotated. The image slider at the bottom allows to navigate through the image set. A slider right next to the image allows to change the level window. On the right side, it is indicated which images are not annotated yet.", html.Br(),
                            html.Br(),
                            "3. After finishing, annotations can be downloaded as csv."])
                )
            ], color="info", inverse=True)
        ], width=3),
        dbc.Col([
            dbc.Progress(
                id="progress_bar",
                value=0,
                label="0%",
                color="success",
                striped=False
            ),
            dbc.Row([
                dcc.Graph(
                    id="plot1",
                    style={"width": "90%", "display": 'None'},
                    responsive=True
                ),
                html.Div([
                    dcc.RangeSlider(
                        id="intensity_slider",
                        min=0,
                        max=1,
                        step=0.01,
                        value=[0., 1.],
                        marks={i: f'{i:1.1f}' for i in np.arange(0, 1, 0.1)},
                        allowCross=False,
                        pushable=0.05,
                        tooltip=dict(always_visible=True, placement="left"),
                        persistence_type="session",
                        disabled=True,
                        vertical=True
                    ),
                ], style={"width": "10%", "display": 'inline-block'}),
            ]),
            dbc.Row([
                html.Div([
                    html.H6([
                        "Image selection",
                    ], style={'display': 'inline-block'}),
                    dbc.Badge(
                        "not annotated",
                        id="file_badge",
                        pill=True,
                        color="primary",
                        style={'display': 'inline-block'}
                    ),
                    dbc.Badge(
                        "accepted",
                        id="file_badge_accepted",
                        color="white",
                        text_color="success",
                        style={'display': 'None'}
                    ),
                    dbc.Badge(
                        "rejected",
                        id="file_badge_rejected",
                        color="white",
                        text_color="danger",
                        style={'display': 'None'}
                    ),
                    dbc.Badge(
                        "skipped",
                        id="file_badge_skipped",
                        color="white",
                        text_color="warning",
                        style={'display': 'None'}
                    ),
                ]),
            ]),
            dbc.Row([
                html.Div([
                    dcc.Slider(
                        id="file_slider",
                        min=1,
                        max=1,
                        step=1,
                        value=1,
                        marks={i+1: str(i+1) for i in range(10)},
                        tooltip=dict(always_visible=True, placement="bottom"),
                        persistence_type="session",
                        disabled=True,
                        vertical=False,
                    ),
                ], style={"width": "90%"}),
                dcc.Input(
                    id="input_circular",
                    type="number",
                    min=1,
                    max=20,
                    value=1,
                    disabled=True,
                    style={"width": "10%"}
                ),
                dbc.Popover([
                    dbc.PopoverHeader("File path"),
                    dbc.PopoverBody("")
                ], id="current_file_popover", target="input_circular", trigger="hover", placement="bottom"
                ),
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Button(
                        u"Accept", #\u2B05
                        id='accept_button',
                        color='success',
                        outline=True,
                        style={'width': '100%'},
                        disabled=True
                    ),
                ], width={'size': 3, 'offset': 1}),
                dbc.Col([
                    dbc.Button(
                        u"Reject", #\u27A1
                        id='reject_button',
                        color='danger',
                        outline=True,
                        style={'width': '100%'},
                        disabled=True
                    )
                ], width={'size': 3, 'offset': 0}),
                dbc.Col([
                    dbc.Button(
                        u"Skip", #\u2B07
                        id='skip_button',
                        color='secondary',
                        outline=True,
                        style={'width': '100%'},
                        disabled=True
                    )
                ], width={'size': 3, 'offset': 0}),
            ]),
        ], width=6),
        dbc.Col([
            dbc.InputGroupText(
                    "Check missing annotations",
                    className="bg-info text-white p-2"
                ),

            dcc.Dropdown(
                id='missing_annotations_dropdown',
                options=[

                ],
                value='None',
                placeholder="Select an image....",
                disabled=True
            ),
            dbc.Popover([
                dbc.PopoverHeader("Check annotations"),
                dbc.PopoverBody("Select from list of un-annotated images")
            ], id="check_annotations_popover", target="missing_annotations_dropdown", trigger="hover", placement="top"
            )
        ], width=3)
    ])
], style={'padding': 40, 'zIndex': 0})


@app.callback(Output("missing_annotations_dropdown", 'options'),
              Input('dummy_load', 'children'),
              Input('dummy_buttons', 'children'),
              Input('dummy_update', 'children'),
              prevent_initial_call=True
              )
def toggle_collapse(_, __, ___):

    not_annotated = DATA.get_unannotated_file_ids()
    options = []

    for file_id in not_annotated:
        options.append({'label': file_id + 1, 'value': file_id + 1})

    return options


def parse_csv(contents) -> pd.DataFrame:
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
    return df


@app.callback(Output("upload", "disabled"),
              Input('upload', 'contents'),
              Input('dummy_load', 'children'),
              prevent_initial_call=True
              )
def update_disabled(_, __):
    ctx = dash.callback_context
    input_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if input_id == "upload":
        return True
    else:
        return False


@app.callback(Output("dummy_update", 'children'),
              Input('upload', 'contents'),
              prevent_initial_call=True
              )
def update_annotations(contents):

    if contents is None:
        raise PreventUpdate
    df = parse_csv(contents)
    DATA.resume_annotation_from_csv(df)
    return []


@app.callback(Output('download', 'data'),
              Input('download_button', 'n_clicks'),
              prevent_initial_call=True
              )
def download_data(_):
    data_pd = DATA.format_data()
    print("#############")
    print(OPERATOR_OUT_DIR)
    if OPERATOR_OUT_DIR:
        csv_export_dir = Path.joinpath(Path(RATEME_FOLDER), OPERATOR_OUT_DIR)
        print("Export csv to: ", csv_export_dir)
        csv_export_dir.mkdir(parents=True, exist_ok=True)
        data_pd.to_csv(Path.joinpath(csv_export_dir, "annotations.csv"), index=False)
    return dcc.send_data_frame(data_pd.to_csv, "annotations.csv")


@app.callback(Output('file_slider', 'marks'),
              Output('file_slider', 'max'),
              Output('file_slider', "disabled"),
              Output('missing_annotations_dropdown', "disabled"),
              Output('input_circular', "disabled"),
              Output('input_circular', 'max'),
              Input('data_path', 'n_submit'),
              State('data_path', 'value'),
              prevent_initial_call=prevent_initial_call
              )
def update_files(_, data_path: str):
    path_exists = True if os.path.isdir(data_path) else False
    DATA.data = {}
    DATA.data_reader = DataReader(base_dir=data_path)
    if DATA.data_reader.n_images > 20:
        marks = {i + 1: str(i + 1) for i in range(0, DATA.data_reader.n_images, int(DATA.data_reader.n_images / 10))}
    else:
        marks = {i + 1: str(i + 1) for i in range(0, DATA.data_reader.n_images)}
    return marks, DATA.data_reader.n_images, False, False, False, DATA.data_reader.n_images


@app.callback(Output('file_slider', 'value'),
              Output('input_circular', 'value'),
              Input('dummy_load', 'children'),
              Input('dummy_buttons', 'children'),
              Input('file_slider', 'value'),
              Input('dummy_update', 'children'),
              Input('input_circular', 'value'),
              Input("missing_annotations_dropdown", 'value'),
              State('file_slider', 'value'),
              prevent_initial_call=True
              )
def update_dummy(_, __, ___, ____, input_value: int, missing_annotation_id: int, file_index: int):
    ctx = dash.callback_context
    input_id = ctx.triggered[0]["prop_id"].split(".")[0]
    if input_id == 'dummy_load':
        value = 1
    elif input_id == "dummy_buttons":
        if file_index == DATA.data_reader.n_images:
            value = file_index
        else:
            value = file_index + 1
    elif input_id == "input_circular":
        value = input_value
    elif input_id == "missing_annotations_dropdown":
        value = missing_annotation_id
    else:
        value = file_index
    return value, value


@app.callback(Output('plot1', 'figure'),
              Output('plot1', 'style'),
              Output('intensity_slider', 'disabled'),
              Output('current_file_popover', 'children'),
              Input('file_slider', 'value'),
              Input('intensity_slider', 'value'),
              prevent_initial_call=True
              )
def update_image(file_index: int, intensity_range):
    if DATA.data_reader is None or file_index is None:
        raise PreventUpdate
    ctx = dash.callback_context
    input_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if input_id == "file_slider":
        norm_range = None
        DATA.data_reader.load_image(index=file_index - 1)
    fig = DATA.data_reader.show_image(norm_range=intensity_range)
    style = {"width": "90%", "display": 'inline-block'}
    popover_children = [
                    dbc.PopoverHeader("File path"),
                    dbc.PopoverBody(f"{DATA.data_reader.data_paths[file_index - 1]}")
                ]
    return fig, style, False, popover_children


@app.callback(Output('accept_button', 'disabled'),
              Output('reject_button', 'disabled'),
              Output('skip_button', 'disabled'),
              Output('dummy_load', 'children'),
              Input('data_path', 'n_submit'),
              Input('user', 'n_submit'),
              State('data_path', 'value'),
              State('user', 'value'),
              prevent_initial_call=prevent_initial_call
              )
def enable_buttons(_, __, data_path: str, user_id: str):
    valid_user_id = True if user_id else False
    valid_data_path = True if os.path.isdir(data_path) else False

    if not valid_user_id or not valid_data_path:
        raise PreventUpdate
    return False, False, False, []


@app.callback(Output('user', 'invalid'),
              Output('user', 'valid'),
              Output('user', 'disabled'),
              Input('user', 'n_submit'),
              Input('user', 'value'),
              prevent_initial_call=prevent_initial_call
              )
def update_user(_, user_id: str):
    valid = True if isinstance(user_id, str) else False
    DATA.user = user_id
    disabled = valid
    if disabled:
        TMP_DATA["user"] = user_id
        disabled = flag_disabled
    return 1 - valid, valid, disabled


@app.callback(Output('data_path', 'invalid'),
              Output('data_path', 'valid'),
              Output('data_path', 'disabled'),
              Input('data_path', 'n_submit'),
              Input('data_path', 'value'),
              prevent_initial_call=prevent_initial_call
              )
def update_path(_, data_path: str):
    valid = True if os.path.isdir(data_path) else False
    disabled = valid
    if disabled:
        TMP_DATA["path"] = data_path
        disabled = flag_disabled
    return bool(1 - valid), valid, disabled


@app.callback(Output('file_badge', 'style'),
              Output('file_badge_accepted', 'style'),
              Output('file_badge_rejected', 'style'),
              Output('file_badge_skipped', 'style'),
              Input('dummy_load', 'children'),
              Input('file_slider', 'value'),
              Input('dummy_update', 'children'),
              State('file_slider', 'value'),
              prevent_initial_call=True
              )
def update_badge(_, __, ___, file_index: int):
    if DATA.data_reader is None or file_index is None:
        raise PreventUpdate

    style_invisible = {'display': 'None'}
    style_visible = {'display': 'inline-block'}

    data_path = DATA.data_reader.get_filename(selected_id=file_index - 1)
    if data_path not in DATA.data:  # not annotated
        return style_visible, style_invisible, style_invisible, style_invisible
    rating = DATA.data[data_path]["choice"]
    if rating == 1:  # accepted
        return style_invisible, style_visible, style_invisible, style_invisible
    elif rating == 0:  # rejected
        return style_invisible, style_invisible, style_visible, style_invisible
    else:  # skipped
        return style_invisible, style_invisible, style_invisible, style_visible


@app.callback(Output('download_button', 'disabled'),
              Output('progress_bar', 'value'),
              Output('progress_bar', 'label'),
              Output('dummy_buttons', 'children'),
              Input('accept_button', 'n_clicks'),
              Input('reject_button', 'n_clicks'),
              Input('skip_button', 'n_clicks'),
              Input('dummy_update', 'children'),
              State('file_slider', 'value'),
              prevent_initial_call=True
              )
def update_accept_button(_, __, ___, ____, file_index: int):
    ctx = dash.callback_context
    input_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if DATA.data_reader is None:
        raise PreventUpdate

    file_name = DATA.data_reader.get_filename(selected_id=file_index - 1)
    if input_id != "dummy_load" and input_id != "dummy_update":
        if input_id == "accept_button": # or keydown["key"] == "a":
            DATA.data[file_name] = Annotation(annotator=DATA.user, time=datetime.now(), choice=1)
        if input_id == 'reject_button': #or keydown["key"] == "r":
            DATA.data[file_name] = Annotation(annotator=DATA.user, time=datetime.now(), choice=0)
        if input_id == 'skip_button': # or keydown["key"] == "s":
            DATA.data[file_name] = Annotation(annotator=DATA.user, time=datetime.now(), choice=np.nan)
    n_annotated = len(DATA.data)
    value_pb = int((n_annotated / DATA.data_reader.n_images)*100)
    label_pb = "{}%".format(value_pb)
    return False, value_pb, label_pb, []


def open_browser(hostname, port):
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        webbrowser.open_new_tab(f"{hostname}:{port}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Run app in debug mode. Changes in code will update the app automatically.")
    parser.add_argument("-p", "--port", type=int,
                        help="Specify the port where the app should run (localhost:port), default is 8050")
    parser.add_argument("-host", "--host_name", type=str,
                        help="Name of the host on which the app is run, by default it is localhost")
    arguments = parser.parse_args()

    port = arguments.port if arguments.port else 8050
    host_name = arguments.host_name if arguments.host_name else "0.0.0.0"
        
    open_browser(hostname=host_name, port=port)
    app.run_server(debug=arguments.debug,
                   host=host_name,
                   port=port)