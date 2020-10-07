import "./brutusin-json-forms.min.js"
import "./brutusin-json-forms.min.css"
// import "./brutusin-json-forms-bootstrap.min.js"

class VisController {
  static metricBtn = document.createElement(`button`);
  static metricDag = document.createElement(`select`);
  static metricBulk = document.createElement(`select`);
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
    this.filterprovider = this.vis.params.filterprovider;

    this.workflow_dialog = null;
    this.dag_list = null;
    this.tmp_metric = null
    VisController.airflow_url = "https://" + window.location.href.split("//")[1].split("/")[0] + "/flow/kaapana/api";
    console.log("airflow_url: " + VisController.airflow_url)
  }

  destroy() {
    this.el.innerHTML = '';
  }

  start_dag() {
    var start = confirm(String(this.tmp_metric.value) + " series will be pushed for processing!\nDo you want to continue?");
    if (!start) {
      return
    } else if (start && this.tmp_metric.value > 100) {
      var result = prompt(String(this.tmp_metric.value) + " series is a lot!\nDo you really want to continue? -> enter 'ok'", "");
      if (result == 'ok') {
        console.log("Start processing!")
      } else {
        console.log("Process cancelled!")
        return
      }
    }

    var dag_id = VisController.metricDag.options[VisController.metricDag.selectedIndex].text.toLowerCase()
    var trigger_url = VisController.airflow_url + "/trigger/meta-trigger"
    // trigger_url = "http://e230-pc15:8080/flow/kaapana/api/trigger/meta-trigger"
    var query = (this.vis.searchSource.history[0].fetchParams.body.query);
    var index = this.vis.searchSource.history[0].fetchParams.index.title;
    var bulk = VisController.metricBulk.options[VisController.metricBulk.selectedIndex].text;
    var conf = {
      "conf": { "query": query, "index": index, "dag": dag_id, bulk: bulk, "form_data": this.dag_form_data }
    };

    var conf_json = JSON.stringify(conf)
    console.log('DAG CONF:')
    console.log(conf_json)
    console.log('URL:');
    console.log(trigger_url);

    fetch(trigger_url, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
      },
      body: conf_json

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

  create_dialog() {
    var bf_pub = null;
    var bf_dag = null;
    this.workflow_dialog.innerHTML = "";
    const BrutusinForms = brutusin["json-forms"];

    const ui_forms = VisController.selected_dag_forms
    const dag_info = VisController.selected_dag_info

    const send_button = document.createElement(`button`);
    send_button.setAttribute("class", "kuiButton kuiButton--secondary")
    send_button.setAttribute('style', "font-weight: bold;font-size: 2em;margin: 10px;height: 50px;");
    send_button.innerHTML = "START"
    send_button.addEventListener('click', () => {
      if (bf_pub.validate()) {
        if (bf_pub.getData().hasOwnProperty("confirmation")) {
          if (!bf_pub.getData()["confirmation"]) {
            alert("You have to confirm first!")
            return
          } else {
            console.log("Confirmation ok.")
          }
        }
      } else {
        alert("Input for form information in not vaild!")
        return
      }
      if (bf_dag.validate()) {
        this.dag_form_data = bf_dag.getData().hasOwnProperty("dag_schema") ? bf_dag.getData()["dag_schema"] : bf_dag.getData();
        this.workflow_dialog.close();
        this.start_dag()
      } else {
        alert("Input for configuration in not vaild!")
        return
      }
    });

    const cancel_button = document.createElement(`button`);
    cancel_button.setAttribute("class", "kuiButton kuiButton--danger")
    cancel_button.setAttribute('style', "font-weight: bold;font-size: 2em;margin: 10px;height: 50px;");
    cancel_button.innerHTML = "CANCEL"
    cancel_button.addEventListener('click', () => {
      this.workflow_dialog.close();
    });

    const head_dialog_div = document.createElement(`div`);
    head_dialog_div.innerHTML = "<h1>DAG: " + VisController.selected_dag_id + "</h1>";
    head_dialog_div.style.paddingTop = '10px'
    head_dialog_div.style.paddingBottom = '15px'
    this.workflow_dialog.appendChild(head_dialog_div)

    const button_div = document.createElement(`div`);
    button_div.setAttribute("style", "text-align: center;");
    button_div.appendChild(send_button)
    button_div.appendChild(cancel_button)

    if (ui_forms != null) {
      const head_pub_div = document.createElement(`div`);
      head_pub_div.innerHTML = "<h2>Information</h2>";
      head_pub_div.style.paddingTop = '10px'
      head_pub_div.style.paddingBottom = '10px'
      this.workflow_dialog.appendChild(head_pub_div)

      const form_pub_div = document.createElement(`div`);
      const form_dag_div = document.createElement(`div`);

      var schema_pub = null;
      var schema_dag = null;

      const workflow_form = ui_forms.hasOwnProperty("workflow_form") ? ui_forms["workflow_form"] : null;
      const publication_form = ui_forms.hasOwnProperty("publication_form") ? ui_forms["publication_form"] : null;

      if (publication_form != null) {
        schema_pub = publication_form;
        bf_pub = BrutusinForms.create(schema_pub);
        bf_pub.render(form_pub_div);
        this.workflow_dialog.appendChild(form_pub_div)
      }

      if (workflow_form != null) {
        const head_dag_div = document.createElement(`div`);
        head_dag_div.innerHTML = "<h2>Configuration</h2>";
        head_dag_div.style.paddingTop = '20px'
        head_dag_div.style.paddingBottom = '10px'
        this.workflow_dialog.appendChild(head_dag_div)

        schema_dag = workflow_form;
        bf_dag = BrutusinForms.create(schema_dag);
        bf_dag.schemaResolver = function (names, data, cb) {
          var schemas = new Object();

          names.forEach(function (item, index) {
            var tmp_schema = new Object();
            var form_field = item.split(".");
            form_field = form_field[form_field.length - 1];
            const schema_template = ui_forms["workflow_form"]["properties"][form_field];

            const depends = schema_template.hasOwnProperty('dependsOn') ? schema_template["dependsOn"] : null;
            data = depends != null && data.hasOwnProperty(depends) ? data[depends] : data;

            tmp_schema.title = schema_template.hasOwnProperty('title') ? schema_template.title : form_field;
            tmp_schema.description = schema_template.hasOwnProperty('description') ? schema_template.description : "NA";
            tmp_schema.readOnly = schema_template.hasOwnProperty('readOnly') ? schema_template.readOnly : false;
            tmp_schema.type = schema_template.hasOwnProperty('type') ? schema_template.type : "string";
            const enum_present = schema_template.hasOwnProperty('enum') ? true : false;

            const insert_data = dag_info[data][form_field];
            if (Array.isArray(insert_data) && enum_present) {
              tmp_schema.enum = insert_data;
              tmp_schema.default = schema_template.hasOwnProperty('default') ? schema_template.default : "";
            } else {
              tmp_schema.default = insert_data + "";
            }
            schemas[item] = tmp_schema;
          });
          cb(schemas);
        };
        bf_dag.render(form_dag_div);
        this.workflow_dialog.appendChild(form_dag_div)
      }
    }

    this.workflow_dialog.appendChild(button_div)
    this.workflow_dialog.show();
  }

  render(visData, status) {
    this.container.innerHTML = '';
    const table = visData
    const metrics = [];
    let bucketAgg;
    var dag_list;
    // var info = table.columns.aggConfig

    this.workflow_dialog = document.createElement(`dialog`);
    this.workflow_dialog.setAttribute("id", "workflow-dialog")
    this.workflow_dialog.style.position = "absolute";
    this.workflow_dialog.style.zIndex = "100";
    document.getElementsByClassName("react-grid-layout dshLayout--viewing")[0].appendChild(this.workflow_dialog);


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
        VisController.metricBulk = document.createElement(`select`);


        VisController.metricBtn.addEventListener('click', () => {
          VisController.selected_dag_id = VisController.metricDag.options[VisController.metricDag.selectedIndex].text;
          var dag_entry = dag_list[VisController.selected_dag_id]

          if (dag_entry.hasOwnProperty('ui_dag_info')) {
            VisController.selected_dag_info = dag_entry['ui_dag_info'];
          } else {
            VisController.selected_dag_info = null;
          }
          if (dag_entry.hasOwnProperty('ui_forms')) {
            VisController.selected_dag_forms = dag_entry['ui_forms']
            this.create_dialog()
          } else {
            this.start_dag()
          }
        });


        function setOptions(list, vis) {
          dag_list = list;
          VisController.metricDag.removeChild(VisController.metricDag.childNodes[0]);
          const dag_ids = Object.keys(dag_list).sort();
          for (var i = 0; i < dag_ids.length; i++) {
            var dag_id = dag_ids[i];
            if (dag_list[dag_id].hasOwnProperty('ui_visible') && !dag_list[dag_id]["ui_visible"]) {
              continue
            }
            var option = document.createElement("option");
            option.value = dag_id;
            option.innerHTML = option.value
            VisController.metricDag.appendChild(option);
          }
        }

        var option = document.createElement("option");
        option.value = "REQUESTING...";
        option.innerHTML = option.value
        VisController.metricDag.appendChild(option);
        VisController.metricDag.style.width = VisController.metricBtn.style.width;
        VisController.metricDag.setAttribute('class', 'btn btn-primary dropdown-toggle')
        VisController.metricDag.setAttribute('style', `font-size: ${this.vis.params.fontSize}pt;`
          + `margin: ${this.vis.params.margin}px;`
          + 'text-align-last:center;'
          + 'width: 95%;');


        var option_bulk1 = document.createElement("option");
        option_bulk1.value = 'SINGLE FILE PROCESSING';
        option_bulk1.innerHTML = option_bulk1.value;
        var option_bulk2 = document.createElement("option");
        option_bulk2.value = 'BATCH PROCESSING';
        option_bulk2.innerHTML = option_bulk2.value;
        VisController.metricBulk.appendChild(option_bulk1);
        VisController.metricBulk.appendChild(option_bulk2);


        VisController.metricBulk.style.width = VisController.metricBtn.style.width;
        VisController.metricBulk.setAttribute('class', 'btn btn-primary dropdown-toggle')
        VisController.metricBulk.setAttribute('style', `font-size: ${this.vis.params.fontSize}pt;`
          + `margin: ${this.vis.params.margin}px;`
          + 'text-align-last:center;'
          + 'width: 95%');


        VisController.metricBtn.innerHTML = this.vis.params.buttonTitle.replace("{{value}}", String(metric.value))
          .replace("{{row}}", metric.row)
          .replace("{{column}}", metric.column);

        VisController.metricBtn.setAttribute('style', `font-size: ${this.vis.params.fontSize}pt;`
          + `margin: ${this.vis.params.margin}px;`
          + 'width: 95%;'
          + 'background-color: #58D68D;');

        VisController.metricBtn.setAttribute('class', 'btn btn-primary')
        this.container.appendChild(VisController.metricDag);
        this.container.appendChild(VisController.metricBulk);
        this.container.appendChild(VisController.metricBtn);

        function getDags(callback, vis) {
          var dagurl = VisController.airflow_url + "/getdags?active_only&dag_info"
          // dagurl = "http://e230-pc15:8080/flow/kaapana/api/getdags?active_only&dag_info"
          console.log("DAGURL: " + dagurl)
          fetch(dagurl, {
            method: 'GET',
            headers: {
              Accept: 'application/json',
            },
          },
          ).then(response => {
            if (response.ok) {
              response.json().then(json => {
                callback(json, vis);

              });
            } else {
              console.error("Could not retrieve dags from server!")
              console.error("Dag-URL: " + dagurl)
              console.log(response.status);
              console.log(response.statusText);
              console.log(response.type);
              console.log(response.url);

            }
          })
            .catch(function (err) {
              console.log('Fetch Error :-S', err);
            });
        }

        if (VisController.metricDag.options[VisController.metricDag.selectedIndex].text === 'REQUESTING...') {
          getDags(setOptions, this.vis)
        }

      });
    }

    return new Promise(resolve => {
      resolve('when done rendering');
    });
  }
};

export { VisController };

