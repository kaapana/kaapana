import "../styles/workflow_trigger_controller.scss"

export const getWorkflowTriggerVisController = (data, getStartServices, buildOpenSearchQuery) => {
  return class VisController {

    constructor(el, vis) {
      // this.vis = vis;
      // VisController.vis = vis;
      this.el = el;

      this.kaapanaBackendUrl = "https://" + window.location.href.split("//")[1].split("/")[0] + "/kaapana-backend"
      this.container = document.createElement('div');
      this.container.className = 'cohortManagement'
      this.cohortNames = []
      this.el.appendChild(this.container);
      
      this.filter_manager = data.query.filterManager;
      getStartServices().then((start_services) => { this.index_patterns = start_services[1].data.indexPatterns});
      this.buildOpenSearchQuery = buildOpenSearchQuery;
      
      // this.getCohortList();
    }

    destroy() {
      this.el.innerHTML = '';
    }

    
    getCohortList() {
      fetch(this.kaapanaBackendUrl + "/client/cohort-names", {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        },
      },
      ).then(response => {
        if (response.ok) {
          console.log("response - ok")
          response.json().then(cohortNames => {
            this.cohortNames = cohortNames
            console.log(cohortNames);
            const cohortSelectionDropDown = document.getElementById("cohortSelection");
            for (var i = cohortSelectionDropDown.length - 1; i >= 0; i--){
              cohortSelectionDropDown.remove(i);
            }
            for (let key in this.cohortNames) {
              let option = document.createElement("option");
              option.setAttribute('value', this.cohortNames[key]);
            
              let optionText = document.createTextNode(this.cohortNames[key]);
              option.appendChild(optionText);
            
              cohortSelectionDropDown.appendChild(option);
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

    deleteCohort(cohortName) {
      fetch(this.kaapanaBackendUrl + "/client/cohort?cohort_name=" + cohortName, {
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
          this.getCohortList();
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


      let cohortName = document.getElementById("cohortName").value;
      if (cohortName == "") {
        alert("Name must be filled out");
        return false;
      }
      var json_schema_data = {
        "cohort_name": cohortName,
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

      fetch(this.kaapanaBackendUrl + "/client/cohort", {
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
            alert("Your cohort was successfully added!")
            console.log(json);
            document.getElementById("cohortNameForm").reset();
            this.getCohortList();
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

      this.getCohortList();

      this.container.innerHTML = '';
      VisController.div_element = document.createElement(`div`);
      VisController.div_element.innerHTML = `
      <form id="cohortNameForm">
        <input id="cohortName" placeholder="Enter a cohort name" type="text" name="cohortName" required>
        <input id="addCohort" type="button" value="Save cohort from query">
      </form>
      <form>
        <select id="cohortSelection" placeholder="Delete a cohort" name="cohortSelection" required></select>
        <input id="selectCohort" type="button" value="Delete cohort">
      </form>
    `;

      this.container.appendChild(VisController.div_element);

      const addCohortButton = document.getElementById("addCohort");
      addCohortButton.addEventListener("click", () => {
        this.startDag();
      });

      const selectCohortButton = document.getElementById("selectCohort");
      selectCohortButton.addEventListener("click", () => {
        let cohortName = document.getElementById("cohortSelection").value;
        this.deleteCohort(cohortName);
      });
    }
  };
}