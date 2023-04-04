import "../styles/workflow_trigger_controller.scss"

export const getWorkflowTriggerVisController = (data, getStartServices, buildOpenSearchQuery) => {
    return class VisController {

        constructor(el, vis) {
            // this.vis = vis;
            // VisController.vis = vis;
            this.el = el;

            this.kaapanaBackendUrl = "https://" + window.location.href.split("//")[1].split("/")[0] + "/kaapana-backend"
            this.container = document.createElement('div');
            this.container.className = 'datasetManagement'
            this.datasetNames = []
            this.el.appendChild(this.container);

            this.filter_manager = data.query.filterManager;
            getStartServices().then((start_services) => {
                this.index_patterns = start_services[1].data.indexPatterns
            });
            this.buildOpenSearchQuery = buildOpenSearchQuery;

            // this.getDatasetList();
        }

        destroy() {
            this.el.innerHTML = '';
        }


        getDatasetList() {
            fetch(this.kaapanaBackendUrl + "/client/datasets", {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                    },
                },
            ).then(response => {
                if (response.ok) {
                    console.log("response - ok")
                    response.json().then(datasetNames => {
                        this.datasetNames = datasetNames.map(dataset => dataset.name)
                        console.log(datasetNames);
                        const datasetSelectionDropDown = document.getElementById("datasetSelection");
                        for (var i = datasetSelectionDropDown.length - 1; i >= 0; i--) {
                            datasetSelectionDropDown.remove(i);
                        }
                        for (let key in this.datasetNames) {
                            let option = document.createElement("option");
                            option.setAttribute('value', this.datasetNames[key]);

                            let optionText = document.createTextNode(this.datasetNames[key]);
                            option.appendChild(optionText);

                            datasetSelectionDropDown.appendChild(option);
                        }

                    });
                } else {
                    console.error("Error while starting the DAG!")
                    console.error(response);
                    alert("ERROR!\nmsg: " + response.type + "\nSee the javascript log for more information.")
                }
            }).catch(function (err) {
                console.log('Fetch Error :-S', err);
            });
        };

        deleteDataset(datasetName) {
            fetch(this.kaapanaBackendUrl + "/client/dataset?name=" + datasetName, {
                    method: 'DELETE',
                    headers: {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                    }
                },
            ).then(response => {
                if (response.ok) {
                    console.log("response - ok");
                    console.log(response);
                    this.getDatasetList();
                } else {
                    console.error("Error while starting the DAG!")
                    console.error(response);
                    alert("ERROR!\nmsg: " + response.type + "\nSee the javascript log for more information.")
                }
            }).catch(function (err) {
                console.log('Fetch Error :-S', err);
            });
        };

        async startDag() {
            if (!this.index_patterns) {
                console.error('indexPatterns prerequisite not ready yet');
                return;
            }

            const filters = this.filter_manager.getFilters();

            var index = filters && filters.length > 0 ? filters[0].meta.index : undefined;

            var index_pattern = index ? await this.index_patterns.get(index) : await this.index_patterns.getDefault();
            if (index) {
                var index_title = (await this.index_patterns.get(index)).title;
            } else {
                var index_title = (await this.index_patterns.getDefault()).title;
            }

            var query = this.buildOpenSearchQuery(index_pattern, [], filters);


            let datasetName = document.getElementById("datasetName").value;
            if (datasetName == "") {
                alert("Name must be filled out");
                return false;
            }

            var json_schema_data = {
                "name": datasetName,
                "query": query
            }

            var json_schema_data_json = JSON.stringify(json_schema_data)
            console.log('DAG CONF:')
            console.log(json_schema_data_json)

            fetch(this.kaapanaBackendUrl + "/client/dataset" + `?query=${json_schema_data_json}`, {
                    method: 'POST',
                    headers: {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                    },
                },
            ).then(response => {
                if (response.ok) {
                    console.log("response - ok")
                    response.json().then(json => {
                        alert("Your dataset was successfully added!")
                        console.log(json);
                        document.getElementById("datasetNameForm").reset();
                        this.getDatasetList();
                    });
                } else {
                    console.error("Error while starting the DAG!")
                    console.error(response);
                    alert("ERROR!\nmsg: " + response.type + "\nSee the javascript log for more information.")
                }
            }).catch(function (err) {
                console.log('Fetch Error :-S', err);
            });
        }


        render(visData, status) {

            this.getDatasetList();

            this.container.innerHTML = '';
            VisController.div_element = document.createElement(`div`);
            VisController.div_element.innerHTML = `
      <form id="datasetNameForm">
        <input id="datasetName" placeholder="Enter a dataset name" type="text" name="datasetName" required>
        <input id="addDataset" type="button" value="Save dataset from query">
      </form>
      <form>
        <select id="datasetSelection" placeholder="Delete a dataset" name="datasetSelection" required></select>
        <input id="selectDataset" type="button" value="Delete dataset">
      </form>
    `;

            this.container.appendChild(VisController.div_element);

            const addDatasetButton = document.getElementById("addDataset");
            addDatasetButton.addEventListener("click", () => {
                this.startDag();
            });

            const selectDatasetButton = document.getElementById("selectDataset");
            selectDatasetButton.addEventListener("click", () => {
                let datasetName = document.getElementById("datasetSelection").value;
                this.deleteDataset(datasetName);
            });
        }
    };
}