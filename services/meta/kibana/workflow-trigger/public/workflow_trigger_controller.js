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
    if (!process.env.NODE_ENV || process.env.NODE_ENV === 'development') {
      VisController.airflow_url = "http://e230-pc15:8080/flow/kaapana/api"
    }
    console.log("airflow_url: " + VisController.airflow_url)
  }

  destroy() {
    this.el.innerHTML = '';
  }

  start_dag() {

    var dag_id = VisController.metricDag.options[VisController.metricDag.selectedIndex].text.toLowerCase()
    var trigger_url = VisController.airflow_url + "/trigger/meta-trigger"

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


  render(visData, status) {
    VisController.series_count=visData.rows[0]['col-0-1'];
    if ($('#workflow_dialog').length <= 0) {
      this.container.innerHTML = '';
      const table = visData
      const metrics = [];
      let bucketAgg;
      var dag_list;
      // var info = table.columns.aggConfig

      this.workflow_dialog = document.createElement(`dialog`);
      this.workflow_dialog.setAttribute("id", "workflow_dialog")
      // this.workflow_dialog.setAttribute('class','fixed');
      this.workflow_dialog.style.backgroundColor = "#F5F5F5";
      this.workflow_dialog.style.opacity = "1";
      this.workflow_dialog.style.position = "fixed";
      this.workflow_dialog.style.top = "30%";
      this.workflow_dialog.style.zIndex = "100";
      this.workflow_dialog.style.width = "50%";
      this.workflow_dialog.style.borderColor = "#FF851B";
      this.workflow_dialog.style.borderWidth = "thick";

      if ($(".dshDashboardViewport-withMargins").length) {
        $(".dshDashboardViewport-withMargins")[0].appendChild(this.workflow_dialog);
      } else {
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
          VisController.metricBulk = document.createElement(`select`);


          VisController.metricBtn.addEventListener('click', () => {
            VisController.selected_dag_id = VisController.metricDag.options[VisController.metricDag.selectedIndex].text;
            if (VisController.selected_dag_id.toLowerCase() === "requesting...") {
              alert("Could not fetch DAG information from kaapana-api!");
              return;
            }
            var dag_entry = dag_list[VisController.selected_dag_id]

            if (dag_entry.hasOwnProperty('ui_dag_info')) {
              VisController.selected_dag_info = dag_entry['ui_dag_info'];
            } else {
              VisController.selected_dag_info = null;
            }
            if (dag_entry.hasOwnProperty('ui_forms')) {
              VisController.selected_dag_forms = dag_entry['ui_forms'];
            } else {
              VisController.selected_dag_forms = null;
            }
            var bf_pub = null;
            var bf_dag = null;
            var bf_status = null;
            this.workflow_dialog.innerHTML = "";
            const BrutusinForms = brutusin["json-forms"];

            const ui_forms = VisController.selected_dag_forms
            const dag_info = VisController.selected_dag_info

            const send_button = document.createElement(`button`);
            send_button.setAttribute("class", "kuiButton kuiButton--secondary");
            send_button.setAttribute("id", "form-ok-button");
            send_button.setAttribute('style', "font-weight: bold;font-size: 2em;margin: 10px;height: 50px;");
            send_button.innerHTML = "START";
            send_button.addEventListener('click', () => {
              if (bf_pub && bf_pub.validate()) {
                if (bf_pub.getData().hasOwnProperty("confirmation")) {
                  if (!bf_pub.getData()["confirmation"]) {
                    alert("You have to confirm the publication-form first!")
                    return
                  } else {
                    console.log("Confirmation ok.")
                  }
                }
              } else if (bf_pub) {
                alert("Input for form information in not vaild!")
                return
              }
              if (bf_dag && bf_dag.validate()) {
                this.dag_form_data = bf_dag.getData().hasOwnProperty("dag_schema") ? bf_dag.getData()["dag_schema"] : bf_dag.getData();
              } else if (bf_dag) {
                alert("Input for configuration in not vaild!")
                return
              }
              if (bf_status && bf_status.validate()) {
                if (bf_status.getData().hasOwnProperty("sure") && !bf_status.getData().sure) {
                  alert("Please confirm the execution (checkbox: ok)!");
                  return
                }
              } else if (bf_status) {
                alert("Input for status-form in not vaild!")
                return
              }
              $('#workflow_dialog').eq(0).hide();
              if (document.getElementsByClassName("react-grid-layout dshLayout--viewing").length == 1) {
                document.getElementsByClassName("react-grid-layout dshLayout--viewing")[0].style.filter = "none"
              }
              this.start_dag()
            });

            const cancel_button = document.createElement(`button`);
            cancel_button.setAttribute("id", "form-cancle-button")
            cancel_button.setAttribute("class", "kuiButton kuiButton--danger")
            cancel_button.setAttribute('style', "font-weight: bold;font-size: 2em;margin: 10px;height: 50px;");
            cancel_button.innerHTML = "CANCEL"
            cancel_button.addEventListener('click', () => {
              $('#workflow_dialog').eq(0).hide();
              if (document.getElementsByClassName("react-grid-layout dshLayout--viewing").length == 1) {
                document.getElementsByClassName("react-grid-layout dshLayout--viewing")[0].style.filter = "none"
              }
            });

            const head_dialog_div = document.createElement(`div`);
            head_dialog_div.innerHTML = "<h1>DAG: " + VisController.selected_dag_id + "</h1>";
            head_dialog_div.style.paddingTop = '10px'
            head_dialog_div.style.paddingBottom = '15px'
            this.workflow_dialog.appendChild(head_dialog_div)

            const series_count_div = document.createElement(`div`);
            series_count_div.setAttribute("id", "series_count_div");
            series_count_div.innerHTML = "<h3>Series-Count: " + VisController.series_count + "</h3>";
            series_count_div.style.paddingTop = '10px'
            series_count_div.style.paddingBottom = '10px'
            this.workflow_dialog.appendChild(series_count_div)

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

                for (let key in schema_pub.properties) {
                  if (!schema_pub.properties[key].hasOwnProperty("description")) {
                    schema_pub.properties[key].description = schema_pub.properties[key].default;
                  }
                };

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
                    tmp_schema.description = schema_template.hasOwnProperty('description') ? schema_template.description : tmp_schema.title;
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

            if (VisController.series_count > 100) {
              const status_form_div = document.createElement(`div`);
              var status_schema = {
                "type": "object",
                "properties": {
                  "warning": {
                    "title": "Warning",
                    "description": "Warning because of many series.",
                    "type": "string",
                    "default": "Trigger " + VisController.series_count + " series?",
                    "readOnly": true
                  },
                  "sure": {
                    "title": "OK",
                    "description": "Yes, I want to trigger that many!",
                    "type": "boolean",
                    "default": false,
                    "required": true
                  }
                }
              };
              bf_status = BrutusinForms.create(status_schema);
              bf_status.render(status_form_div);
              this.workflow_dialog.appendChild(status_form_div)
            }

            this.workflow_dialog.appendChild(button_div)
            $('#series_count_div').innerHTML = "<h3>Series-Count: " + VisController.series_count + "</h3>";
            $('#workflow_dialog').eq(0).show();
            document.getElementById("form-ok-button").focus();
            if (document.getElementsByClassName("react-grid-layout dshLayout--viewing").length == 1) {
              document.getElementsByClassName("react-grid-layout dshLayout--viewing")[0].style.filter = "blur(5px)"
            }
          });


          function setOptions(list, vis) {
            dag_list = list;
            VisController.metricDag.innerHTML = "";
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
          VisController.metricDag.setAttribute('id', 'dag_dropdown')
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


          VisController.metricBtn.innerHTML = this.vis.params.buttonTitle.replace("{{value}}", String(VisController.series_count))
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
    } else {
      VisController.metricBtn.innerHTML = this.vis.params.buttonTitle.replace("{{value}}", VisController.series_count)
    }
  }
};

export { VisController };


document.onkeydown = function (evt) {
  if ($('#workflow_dialog').length > 0 && $('#workflow_dialog').get(0).style.display === "block") {
    evt = evt || window.event;
    if (evt.keyCode === 27 || (evt.key === "Escape" || evt.key === "Esc")) {
      document.getElementById("form-cancle-button").click();
    } else if (evt.key === "Enter" || evt.keyCode == 13) {
      document.getElementById("form-ok-button").focus();
    }
  }
};

