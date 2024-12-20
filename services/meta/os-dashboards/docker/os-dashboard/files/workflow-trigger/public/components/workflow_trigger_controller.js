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
            this.project_dropdown_index = "";
            getStartServices().then((start_services) => {
                this.index_patterns = start_services[1].data.indexPatterns; 
            });
            this.buildOpenSearchQuery = buildOpenSearchQuery;
        }

        destroy() {
            this.el.innerHTML = '';
        }

        async fetchProjectsByName(indexPatternTitle) {
            const url = `/meta/api/opensearch-dashboards/suggestions/values/${indexPatternTitle}`;
            const body = JSON.stringify({
                boolFilter: [],
                field: "_index",
                query: ""
            });
        
            try {
                const response = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'osd-xsrf': 'true',
                    },
                    body,
                });
        
                if (!response.ok) {
                    throw new Error(`Failed to fetch project names: ${response.statusText}`);
                }
        
                const project_names = await response.json();
                return project_names;
            } catch (error) {
                console.error("Error fetching project names:", error);
            }
        }

        async updateDashboardFilter(index) {
            this.project_dropdown_index = index;            
            const filters = this.filter_manager.getFilters();
        
            // Check if there are filters related to `_index` and extract the project value
            const projectFilters = filters.filter(
                (filter) => filter.meta?.key === "_index"
            );        
            // Remove all projectFilters that do not match the given index
            projectFilters.forEach((filter) => {
                if (filter.meta?.params?.query !== index) {
                    this.filter_manager.removeFilter(filter); // Remove non-matching filters
                }
            });
        
            // If the index is empty, no need to add a new filter
            if (index === "") {
                return;
            }
        
            // Create and add the new filter
            const filterQuery = {
                meta: {
                    index: "project_",
                },
                query: {
                    match_phrase: {
                        _index: index,
                    },
                },
            };
        
            this.filter_manager.addFilters(filterQuery);
        }
        

        async fillProjectDropDown(){
            const filters = this.filter_manager.getFilters();
            var index = filters && filters.length > 0 ? filters[0].meta.index : undefined;   
            if (index) {
                var index_title = (await this.index_patterns.get(index)).title;
            } else {
                var index_title = (await this.index_patterns.getDefault()).title;
            }

            var index_list = await this.fetchProjectsByName(index_title);
            return index_list
        }
        async saveDataset() {
            if (!this.index_patterns) {
                console.error('indexPatterns prerequisite not ready yet');
                return;
            }
            const filters = this.filter_manager.getFilters();
            var index = filters && filters.length > 0 ? filters[0].meta.index : undefined;            
            var index_pattern = index ? await this.index_patterns.get(index) : await this.index_patterns.getDefault();
            
            const projectFilter = filters.filter(
                (filter) => filter.meta?.key === "_index"
            );

            if (projectFilter.length != 1){
                alert("A project has to be selected.")
                return false;
            }
            
            var query = this.buildOpenSearchQuery(index_pattern, [], filters);
            let datasetName = document.getElementById("datasetName").value;
            if (datasetName == "") {
                alert("Name must be filled out.");

                return false;
            }
            var json_schema_data = {
                "name": datasetName,
                "query": query,
            }

            var json_schema_data_json = JSON.stringify(json_schema_data)
            console.log('DAG CONF:')
            console.log(json_schema_data_json)

            fetch(this.kaapanaBackendUrl + "/client/dataset-from-query", {
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
                        alert("Your dataset was successfully added!")
                        console.log(json);
                        document.getElementById("datasetNameForm").reset();
                    });
                } else {
                    console.error("Error while saving the dataset!");
                    console.error(`Status: ${response.status} - ${response.statusText}`);
                    response.json().then(errorJson => {
                        console.error("Error details:", errorJson);
                        alert(`ERROR!\nStatus: ${response.status}\nMessage: ${errorJson.message || response.statusText}\nSee the JavaScript console for more information.`);
                    }).catch(() => {
                        // If parsing the JSON fails, just display status text
                        alert(`ERROR!\nStatus: ${response.status}\nMessage: ${response.statusText}\nSee the JavaScript console for more information.`);
                    });
                }
            }).catch(function (err) {
                console.log('Fetch Error :-S', err);
            });
        }



        async render(visData, status) {
            this.container.innerHTML = '';
            VisController.div_element = document.createElement(`div`);
            VisController.div_element.innerHTML = `
        <form>
            <select id="projectSelection" placeholder="Select a project" ></select>
        </form>
        <form id="datasetNameForm">
            <input id="datasetName" placeholder="Enter a dataset name" type="text" name="datasetName" required>
            <input id="addDataset" type="button" value="Save as dataset">
        </form>
    `;

            this.container.appendChild(VisController.div_element);
            const project_dropdown = document.getElementById("projectSelection");
            //Add empty object to and filternames
            const project_names = ["", ...(await this.fillProjectDropDown())];
            project_names.forEach(index => {
                const option = document.createElement('option');
                option.value = index;
                option.textContent = index;
                project_dropdown.appendChild(option);
            });
            project_dropdown.value = this.project_dropdown_index;
            project_dropdown.addEventListener('change', event => {
                const selectedIndex = event.target.value;
                this.updateDashboardFilter(selectedIndex);
            });


            const addDatasetButton = document.getElementById("addDataset");
            addDatasetButton.addEventListener("click", () => {
                this.saveDataset();
            });
        }
    };
}
