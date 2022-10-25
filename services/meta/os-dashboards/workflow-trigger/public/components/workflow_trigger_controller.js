import "../dependencies/brutusin-json-forms.min.js"
import "../dependencies/brutusin-json-forms.min.scss"
import "../styles/workflow_trigger_controller.scss"

export const getWorkflowTriggerVisController = (data, getStartServices, buildOpenSearchQuery) => {
return class VisController {
  static metricBtn = document.createElement(`button`);
  static metricDag = document.createElement(`select`);
  static airflow_url = null;
  static selected_dag_id = null;
  static selected_dag_info = null;
  static selected_dag_forms = null;
  static vis = null;

  constructor(el, vis) {
    this.vis = vis;
    VisController.vis = vis;
    this.el = el;

    this.container = document.createElement('div');
    this.container.className = 'myvis-container-div';
    this.el.appendChild(this.container);
    
    this.filter_manager = data.query.filterManager;
    getStartServices().then((start_services) => { this.index_patterns = start_services[1].data.indexPatterns});
    this.buildOpenSearchQuery = buildOpenSearchQuery;

    this.workflow_dialog = null;
    this.dag_list = null;
    this.tmp_metric = null
    VisController.airflow_url = "https://" + window.location.href.split("//")[1].split("/")[0] + "/flow/kaapana/api";
    VisController.kaapana_backend_url = "https://" + window.location.href.split("//")[1].split("/")[0] + "/kaapana-backend/client";
    if (!process.env.NODE_ENV || process.env.NODE_ENV === 'development') {
      VisController.airflow_url = "http://e230-pc15:8080/flow/kaapana/api"
    }
    console.log("airflow_url: " + VisController.airflow_url)
    console.log("kaapana_backend_url: " + VisController.kaapana_backend_url)
  }

  destroy() {
    this.el.innerHTML = '';
  }

  async start_dag() {
    if (!this.index_patterns) {
      console.error('indexPatterns prerequisite not ready yet');
      return;
    }

    var trigger_url = VisController.kaapana_backend_url + "/cohort"

    const filters = this.filter_manager.getFilters();

    var index = filters && filters.length > 0 ? filters[0].meta.index : undefined;

    var index_pattern = index ? await this.index_patterns.get(index) : await this.index_patterns.getDefault();
    if (index) {
      var index_title = (await this.index_patterns.get(index)).title;
    } else {
      var index_title = (await this.index_patterns.getDefault()).title;
    }

    var query = this.buildOpenSearchQuery(index_pattern, [], filters);

    var json_schema_data = {
      "cohort_name": VisController.cohort_name,
      "cohort_query": {
        "index": [index_title],
        "query_dict": {
          "query": query,
          "_source": ['dataset_tags_keyword']
          }
      }
    }

    var json_schema_data_json = JSON.stringify(json_schema_data)
    console.log('DAG CONF:')
    console.log(json_schema_data_json)
    console.log('URL:');
    console.log(trigger_url);

    fetch(trigger_url, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
      },
      body: json_schema_data_json

    },
    ).then(response => {
      if (response.ok) {
        console.log("response - ok")
        response.json().then(json => {
          alert("Your request was successful!")
          console.log(json);
        });
      } else {
        console.error("Error while starting the DAG!")
        console.error("POST-URL: " + trigger_url)
        console.error(response.status);
        console.error(response.statusText);
        console.error(response.type);
        console.error(response.url);
        console.error(response);
        alert("ERROR!\nmsg: " + response.type + "\nSee the javascript log for more information.")
      }
    })
      .catch(function (err) {
        console.log('Fetch Error :-S', err);
      });
  }


  render(visData, status) {
    // VisController.series_count = visData.rows[0]['col-0-1'];
    console.log(visData);
    if ($('#workflow_dialog').length <= 0) {
      console.log('hello');
      this.container.innerHTML = '';
      const table = visData
      const metrics = [];
      let bucketAgg;

      this.workflow_dialog = document.createElement(`dialog`);
      this.workflow_dialog.setAttribute("id", "workflow_dialog")
      // this.workflow_dialog.setAttribute('class','fixed');
      this.workflow_dialog.style.backgroundColor = "#F5F5F5";
      this.workflow_dialog.style.opacity = "1";
      this.workflow_dialog.style.position = "fixed";
      this.workflow_dialog.style.top = "20%";
      this.workflow_dialog.style.zIndex = "100";
      this.workflow_dialog.style.width = "50%";
      this.workflow_dialog.style.borderColor = "#FF851B";
      this.workflow_dialog.style.borderWidth = "thick";

      if ($(".dshDashboardViewport-withMargins").length) {
        console.log('hmmm');
        $(".dshDashboardViewport-withMargins")[0].appendChild(this.workflow_dialog);
      } else {
        console.log('adding');
        this.container.appendChild(this.workflow_dialog);
      }

      if (table) {
        table.columns.forEach((column, i) => {
          // we have multiple rows … first column is a bucket agg
          if (table.rows.length > 1 && i == 0) {
            bucketAgg = column.aggConfig;
            return;
          }

          table.rows.forEach(row => {
            const value = row['col-0-1'];
            metrics.push({
              title: bucketAgg ? `${row[0]} ${column.title}` : column.title,
              column: column.title,
              value: value,
              formattedValue: column.aggConfig ? column.aggConfig.fieldFormatter('text')(value) : value,
              bucketValue: bucketAgg ? row[0] : null,
              aggConfig: column.aggConfig
            });
          });
        });
        this.tmp_metric = metrics[0]

        metrics.forEach(metric => {
          VisController.metricBtn = document.createElement(`button`);
          VisController.metricDag = document.createElement(`select`);

          VisController.metricBtn.addEventListener('click', () => {
            var bf_status = null;
            this.workflow_dialog.innerHTML = ""
            const BrutusinForms = brutusin["json-forms"];

            const status_form_div = document.createElement(`div`);
            var status_schema = {
              "type": "object",
              "properties": {
                "cohort_name": {
                  "title": "Name of cohort",
                  "type": "string",
                  "description": "Name of cohort.",
                  "required": true
                }
              }
            };
            bf_status = BrutusinForms.create(status_schema);
            bf_status.render(status_form_div);
            this.workflow_dialog.appendChild(status_form_div)

            const send_button = document.createElement(`button`);
            send_button.setAttribute("class", "kuiButton kuiButton--secondary");
            send_button.setAttribute("id", "form-ok-button");
            send_button.setAttribute('style', "font-weight: bold;font-size: 2em;margin: 10px;height: 50px;");
            send_button.innerHTML = this.vis.params.buttonTitle;
            send_button.addEventListener('click', () => {
              if (bf_status && bf_status.validate()) {
                if (bf_status.getData().hasOwnProperty("cohort_name")) {
                  VisController.cohort_name = bf_status.getData().cohort_name
                }
              } else if (bf_status) {
                alert("Input for status-form in not vaild!")
                return
              }

              $('#workflow_dialog').eq(0).hide();
              if (document.getElementsByClassName("react-grid-layout dshLayout--viewing").length == 1) {
                document.getElementsByClassName("react-grid-layout dshLayout--viewing")[0].style.filter = "none";
                document.getElementsByClassName("react-grid-layout dshLayout--viewing")[0].style.pointerEvents = "auto";
              }
              this.start_dag()
            });

            const cancel_button = document.createElement(`button`);
            cancel_button.setAttribute("id", "form-cancel-button")
            cancel_button.setAttribute("class", "kuiButton kuiButton--danger")
            cancel_button.setAttribute('style', "font-weight: bold;font-size: 2em;margin: 10px;height: 50px;");
            cancel_button.innerHTML = "CANCEL"
            cancel_button.addEventListener('click', () => {
              $('#workflow_dialog').eq(0).hide();
              if (document.getElementsByClassName("react-grid-layout dshLayout--viewing").length == 1) {
                document.getElementsByClassName("react-grid-layout dshLayout--viewing")[0].style.filter = "none";
                document.getElementsByClassName("react-grid-layout dshLayout--viewing")[0].style.pointerEvents = "auto";
              }
            });

            const button_div = document.createElement(`div`);
            button_div.setAttribute("style", "text-align: center;");
            button_div.appendChild(send_button)
            button_div.appendChild(cancel_button)

            this.workflow_dialog.appendChild(button_div)
            $('#workflow_dialog').eq(0).show();
            if (document.getElementsByClassName("react-grid-layout dshLayout--viewing").length == 1) {
              document.getElementsByClassName("react-grid-layout dshLayout--viewing")[0].style.filter = "blur(5px)";
              document.getElementsByClassName("react-grid-layout dshLayout--viewing")[0].style.pointerEvents = "none";
            }
          });

          VisController.metricBtn.innerHTML = this.vis.params.buttonTitle.replace("{{value}}", String(VisController.series_count))
            .replace("{{row}}", metric.row)
            .replace("{{column}}", metric.column);

          VisController.metricBtn.setAttribute('style', `font-size: ${this.vis.params.fontSize}pt;`
            + `margin: ${this.vis.params.margin}px;`
            + 'width: 95%;'
            + 'background-color: #58D68D;');

          VisController.metricBtn.setAttribute('class', 'btn btn-primary')
          this.container.appendChild(VisController.metricBtn);

        });
      }    
      return new Promise(resolve => {
        resolve('when done rendering');
      });
    }
  }
};


}
document.onkeydown = function (evt) {
  if ($('#workflow_dialog').length > 0 && $('#workflow_dialog').get(0).style.display === "block") {
    evt = evt || window.event;
    if (evt.keyCode === 27 || (evt.key === "Escape" || evt.key === "Esc")) {
      document.getElementById("form-cancel-button").click();
    } else if (evt.key === "Enter" || evt.keyCode == 13) {
      document.getElementById("form-ok-button").focus();
    }
  }
};
