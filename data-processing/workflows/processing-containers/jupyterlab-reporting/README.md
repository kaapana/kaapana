# jupyterlab-reporting

Execute Jupyter notebooks against pipeline outputs. Replaces `JupyterlabReportingOperator`.

## Templates needed

- `run-notebook`: execute a notebook from the `notebook` input channel against the `data` input channel and emit HTML/PDF (controlled by `OUTPUT_FORMAT`) to the `report` output channel.
