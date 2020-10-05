import "./brutusin-json-forms.min.js"
import "./brutusin-json-forms.min.css"
// import "./brutusin-json-forms-bootstrap.min.js"

class VisController {
  static metricBtn = document.createElement(`button`);
  static metricDag = document.createElement(`select`);
  static metricBulk = document.createElement(`select`);
  static airflow_url = null;
  static selected_dag_info = null;
  static vis = null;

  constructor(el, vis) {
    this.vis = vis;
    VisController.vis = vis;
    console.error(VisController.vis)
    this.el = el;

    this.container = document.createElement('div');
    this.container.className = 'myvis-container-div';
    this.el.appendChild(this.container);
    this.filterprovider = this.vis.params.filterprovider;

    this.workflow_dialog = null;
    this.dag_list = null;
    this.tmp_metric = null
    VisController.airflow_url = "https://" + window.location.href.split("//")[1].split("/")[0] + "/flow/kaapana/api";
    console.error("airflow_url: " + VisController.airflow_url)
  }

  destroy() {
    this.el.innerHTML = '';
  }

  start_dag() {
    if (VisController.selected_dag_info != null && VisController.selected_dag_info.hasOwnProperty('modality')) {
      console.error("Found modality check!")
      var modalities = VisController.selected_dag_info['modality']
      console.error(modalities)

      if (!Array.isArray(modalities)) {
        modalities = [modalities]
      }

      console.error(this.tmp_metric)


    }

    var start = confirm(String(this.tmp_metric.value) + " series will be pushed for processing!\nDo you want to continue?");
    if (!start) {
      return
    } else if (start && this.tmp_metric.value > 100) {
      var result = prompt(String(this.tmp_metric.value) + " series is a lot!\nDo you really want to continue? -> enter 'ok'", "");
      if (result == 'ok') {
        console.log("Start processing!")
      } else {
        console.log("Pushing cancelled!")
        return
      }
    }

    var dag_id = VisController.metricDag.options[VisController.metricDag.selectedIndex].text.toLowerCase()
    var trigger_url = VisController.airflow_url + "/trigger/meta-trigger"
    trigger_url = "http://e230-pc15:8080/flow/kaapana/api/trigger/meta-trigger"
    var query = (this.vis.searchSource.history[0].fetchParams.body.query);
    var index = this.vis.searchSource.history[0].fetchParams.index.title;
    var bulk = VisController.metricBulk.options[VisController.metricBulk.selectedIndex].text;
    var conf = {
      "conf": { "query": query, "index": index, "dag": dag_id, bulk: bulk, "form_data": this.form_data }
    };

    var conf_json = JSON.stringify(conf)
    console.log('CONF: \n' + conf_json)
    console.log('URL: ' + trigger_url);

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
    const dag_info = VisController.selected_dag_info
    console.error("+++++++++++++++++++++++++++++++++++++++++++++++++++")
    console.error(dag_info)
    console.error("+++++++++++++++++++++++++++++++++++++++++++++++++++")
    this.workflow_dialog.innerHTML = "";

    const BrutusinForms = brutusin["json-forms"];
    var additional_prop = []
    var confirmation = false
    var tbl = null

    const publication = dag_info.hasOwnProperty('publication') && dag_info['publication'].hasOwnProperty("title") && dag_info['publication'].hasOwnProperty("authors") && dag_info['publication'].hasOwnProperty("doi")
    const workflow_form = dag_info.hasOwnProperty('form_schema')


    console.error("publication: " + publication)
    console.error("workflow_form: " + workflow_form)

    const send_button = document.createElement(`button`);
    send_button.setAttribute("class", "kuiButton kuiButton--secondary")
    send_button.setAttribute('style', "font-weight: bold;font-size: 2em;margin: 10px;height: 50px;");
    send_button.innerHTML = "START"
    send_button.addEventListener('click', () => {
      if (bf.validate()) {
        this.form_data = bf.getData();
        if (confirmation && (this.form_data == null || (this.form_data.hasOwnProperty('confirmation') && this.form_data['confirmation'].toLowerCase() !== "ok"))) {
          alert("You have to confirm this with 'ok'")
        } else {
          this.workflow_dialog.close();
          this.start_dag()
        }
      } else {
        alert("Input in not vaild!")
      }
    });

    const cancel_button = document.createElement(`button`);
    cancel_button.setAttribute("class", "kuiButton kuiButton--danger")
    cancel_button.setAttribute('style', "font-weight: bold;font-size: 2em;margin: 10px;height: 50px;");
    cancel_button.innerHTML = "CANCEL"
    cancel_button.addEventListener('click', () => {
      this.workflow_dialog.close();
    });

    const form_div = document.createElement(`div`);
    const button_div = document.createElement(`div`);
    button_div.setAttribute("style", "text-align: center;");
    button_div.appendChild(send_button)
    button_div.appendChild(cancel_button)

    if (publication) {
      const pub_info = dag_info['publication']

      tbl = document.createElement('table');
      tbl.style.width = '100%';
      tbl.setAttribute('border', '1');
      var tbdy = document.createElement('tbody');
      var tr_button = document.createElement('tr');
      var tr_1 = document.createElement('tr');
      tr_1.setAttribute("style", "font-size: 1em;margin: 20px;padding: 10px;");

      var tr_2 = document.createElement('tr');
      tr_2.setAttribute("style", "font-size: 1em;margin: 20px;padding: 10px;");
      var tr_3 = document.createElement('tr');
      tr_3.setAttribute("style", "font-size: 1em;margin: 20px;padding: 10px;");

      tbdy.appendChild(tr_1);
      tbdy.appendChild(tr_3);
      tbdy.appendChild(tr_2);

      var td_1_1 = document.createElement('td');
      td_1_1.setAttribute('style', "font-weight: bold;font-size: 1em;");
      td_1_1.appendChild(document.createTextNode('Title: '));
      var td_1_2 = document.createElement('td');
      td_1_2.appendChild(document.createTextNode(pub_info["title"]));
      tr_1.appendChild(td_1_1)
      tr_1.appendChild(td_1_2)
      var td_2_1 = document.createElement('td');
      td_2_1.appendChild(document.createTextNode('Authors: '));
      td_2_1.setAttribute('style', "font-weight: bold;font-size: 1em;");
      var td_2_2 = document.createElement('td');
      td_2_2.appendChild(document.createTextNode(pub_info["authors"]));
      tr_2.appendChild(td_2_1)
      tr_2.appendChild(td_2_2)
      var td_3_1 = document.createElement('td');
      td_3_1.setAttribute('style', "font-weight: bold;font-size: 1em;");
      td_3_1.appendChild(document.createTextNode('DOI: '));
      var td_3_2 = document.createElement('td');
      td_3_2.appendChild(document.createTextNode(pub_info["doi"]));
      tr_3.appendChild(td_3_1)
      tr_3.appendChild(td_3_2)
      tbl.appendChild(tbdy);
      form_div.appendChild(tbl)

      if (pub_info["confirmation"]) {
        confirmation = true
        additional_prop.push({
          "confirmation": {
            "title": "confirmation",
            "description": "Please enter ok to confirm.",
            "type": "string",
            "required": 'true'
          }
        }
        )
      }
    }

    var schema = {
      "type": "object",
      "properties": {
      }
    }
    if (workflow_form) {
      schema = dag_info['form_schema']
    }

    var arrayLength = additional_prop.length;
    for (var i = 0; i < arrayLength; i++) {
      const key = Object.keys(additional_prop[i])[0];
      schema["properties"][key] = additional_prop[i][key]
    }
    const bf = BrutusinForms.create(schema);

    bf.schemaResolver = function (names, data, cb) {
      var schemas = new Object();
      console.error("in schemaResolver");
      console.error(names);

      names.forEach(function (item, index) {
        var schema = new Object();
        const form_field = item.split(".")[1];
        const insert_data = dag_info["tasks"][data.task][form_field];
        const schema_template = dag_info["form_schema"]["properties"][form_field];

        schema.title = schema_template.hasOwnProperty('title') ? schema_template.title : form_field;
        schema.description = schema_template.hasOwnProperty('description') ? schema_template.description : "NA";
        schema.readOnly = schema_template.hasOwnProperty('readOnly') ? schema_template.readOnly : false;
        schema.type = schema_template.hasOwnProperty('type') ? schema_template.type : "string";
        const enum_present = schema_template.hasOwnProperty('enum') ? true : false;

        if (Array.isArray(insert_data) && enum_present) {
          schema.enum = insert_data;
          schema.default = schema_template.hasOwnProperty('default') ? schema_template.default : "";
        } else if (Array.isArray(insert_data) && !enum_present) {
          schema.default = insert_data + "";
        } else {
          schema.default = insert_data + "";
        }
        schemas[item] = schema;
      });
      setTimeout(function () { cb(schemas) }, 500); // in order to show asynchrony
    };
    bf.render(form_div);

    this.workflow_dialog.appendChild(form_div)
    this.workflow_dialog.appendChild(button_div)
    this.workflow_dialog.show();
  }

  render(visData, status) {
    this.container.innerHTML = '';
    const table = visData
    const metrics = [];
    let bucketAgg;
    var dag_list;
    var info = table.columns.aggConfig

    this.workflow_dialog = document.createElement(`dialog`);
    this.workflow_dialog.setAttribute("id", "workflow-dialog")
    // workflow_dialog.setAttribute("style","width:50%;background-color:#F4FFEF;border:1px dotted black;")
    this.container.appendChild(this.workflow_dialog)

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
          var dag_id = VisController.metricDag.options[VisController.metricDag.selectedIndex].text.toLowerCase();
          var dag_entry = dag_list[dag_id]
          if (dag_entry.hasOwnProperty('dag_info')) {
            VisController.selected_dag_info = dag_entry['dag_info']
            if (VisController.selected_dag_info.hasOwnProperty('form_schema') || VisController.selected_dag_info.hasOwnProperty('publication')) {
              this.create_dialog()
            } else {
              this.start_dag()
            }
          } else {
            VisController.selected_dag_info = null;
            this.start_dag();
          }
        });


        function setOptions(list, vis) {
          dag_list = list;
          VisController.metricDag.removeChild(VisController.metricDag.childNodes[0]);
          const dag_ids = Object.keys(dag_list);
          for (var i = 0; i < dag_ids.length; i++) {
            var dag_id = dag_ids[i];

            if (dag_list[dag_id].hasOwnProperty('dag_info') && dag_list[dag_id]["dag_info"].hasOwnProperty('visible') && !dag_list[dag_id]["dag_info"]["visible"]) {
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

        // var form_div = document.createElement("div");
        // f.setAttribute('method',"post");
        // form_div.src = './test.html';;
        // form_div.innerHTML='<object type="text/html" data="home.html" ></object>';

        // this.container.appendChild(form_div);

        function getDags(callback, vis) {
          var dagurl = VisController.airflow_url + "/getdags?active_only&dag_info"
          dagurl = "http://e230-pc15:8080/flow/kaapana/api/getdags?active_only&dag_info"
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

