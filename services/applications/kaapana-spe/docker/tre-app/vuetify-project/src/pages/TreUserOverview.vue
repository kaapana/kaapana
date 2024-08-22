<template>
  <v-container>
    <v-row>
      <v-col>
        <h2>Your Trusted Research Environments</h2>
      </v-col>
    </v-row>

    <!-- List of TREs -->
    <v-row v-for="(tre, index) in tres" :key="index">
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <v-row>
              <v-col cols="6" class="d-flex align-center">
                <v-icon 
                  v-if="tre.status === 'accepted'" 
                  color="green"
                  class="mr-2"
                >mdi-check-circle</v-icon>
                <v-icon 
                  v-if="tre.status === 'pending'" 
                  color="orange"
                  class="mr-2"
                >mdi-clock-outline</v-icon>
                <v-icon 
                  v-if="tre.status === 'denied'" 
                  color="red"
                  class="mr-2"
                >mdi-close-circle</v-icon>
                <div class="text-left plain-text">{{ tre.name }}</div>
              </v-col>
              <v-col cols="6" class="text-right">
                <v-btn
                  color="secondary"
                  @click="tre.expanded = !tre.expanded"
                >
                  Details
                </v-btn>
                <v-btn
                  :href="tre.link"
                  target="_blank"
                  color="success"
                >
                  <v-icon>mdi-open-in-new</v-icon>
                </v-btn>
              </v-col>
            </v-row>
          </v-card-title>
          <v-expand-transition>
            <v-card-text v-if="tre.expanded" class="transparent-text">
              <div><strong>Project:</strong> {{ tre.project }}</div>
              <div><strong>Description:</strong> {{ tre.details }}</div>
              <div><strong>Memory:</strong> {{ tre.memory }} GB</div>
              <div><strong>Storage:</strong> {{ tre.storage }} GB</div>
              <div><strong>GPU:</strong> {{ tre.gpu }}</div>
              <div><strong>Owner:</strong> {{ tre.owner }}</div>
              <div><strong>User:</strong> {{ tre.user }}</div>
              <div><strong>Status:</strong> {{ tre.status }}</div>
            </v-card-text>
          </v-expand-transition>
        </v-card>
      </v-col>
    </v-row>

    <!-- Button to create new TRE -->
    <v-row>
      <v-col>
        <v-btn
          color="primary"
          @click="formExpanded = !formExpanded"
          :class="{'hovered-button': formExpanded}"
        >
          <v-icon v-if="!formExpanded">mdi-plus</v-icon>
          <span v-if="formExpanded">Cancel</span>
        </v-btn>
      </v-col>
    </v-row>

    <!-- Form to create new TRE -->
    <v-expand-transition>
      <v-row v-if="formExpanded">
        <v-col cols="12">
          <v-form @submit.prevent="submitNewTRE">
            <v-select
              v-model="newTRE.project"
              :items="projectNames"
              label="Select Project"
              required
              dense
              outlined
              :menu-props="{ maxHeight: '300px' }"
              class="project-select"
            ></v-select>
            <v-text-field
              v-model="newTRE.name"
              label="TRE Name"
              required
            ></v-text-field>
            <v-textarea
              v-model="newTRE.description"
              label="TRE Description"
              required
            ></v-textarea>
            <v-text-field
              v-model="newTRE.memory"
              label="Memory (GB)"
              type="number"
              required
            ></v-text-field>
            <v-text-field
              v-model="newTRE.storage"
              label="Storage (GB)"
              type="number"
              required
            ></v-text-field>
            <v-text-field
              v-model="newTRE.gpu"
              label="GPU"
              required
            ></v-text-field>
            <v-text-field
              v-model="newTRE.owner"
              label="Owner"
              required
            ></v-text-field>
            <v-text-field
              v-model="newTRE.user"
              label="User"
              required
            ></v-text-field>
            <v-btn
              type="submit"
              color="success"
            >
              Submit
            </v-btn>
          </v-form>
        </v-col>
      </v-row>
    </v-expand-transition>
  </v-container>
</template>

<script>
import axios from 'axios';

export default {
  data() {
    return {
      tres: [],
      projectNames: [],  // To store the list of project names
      selectedProject: '',  // Store the selected project name from the dropdown
      formExpanded: false,
      newTRE: {
        project: '',  // Selected project name
        name: '',
        description: '',
        memory: 0,
        storage: 0,
        gpu: '',
        owner: '',
        user: '',
      },
    };
  },
  created() {
    this.fetchTREs();
    if (!this.$root.projectsLoaded) {  // Check if project names are already loaded
      this.fetchProjects();  // Fetch available project names only if not already loaded
    } else {
      this.projectNames = this.$root.projectNamesList;  // Use the already loaded project names
    }
  },
  methods: {
    async fetchTREs() {
      try {
        const response = await axios.get('http://127.0.0.1:8000/api/environments/');
        if (Array.isArray(response.data)) {
          this.tres = response.data.map(env => ({
            name: env.name,
            project: env.project,
            link: `https://example.com/tre${env.id}`,
            expanded: false,
            details: env.description,
            memory: env.memory,
            storage: env.storage,
            gpu: env.gpu,
            owner: env.owner,
            user: env.user,
            status: env.status,
          }));
        } else {
          console.error('API response is not an array:', response.data);
        }
      } catch (error) {
        console.error('Error fetching TREs:', error);
      }
    },
    async fetchProjects() {
      try {
        const response = await axios.get('http://127.0.0.1:8000/api/projects');  // Adjust the endpoint as needed
        if (Array.isArray(response.data)) {
          this.projectNames = response.data.map(project => project.name);  // Extract just the project names
          this.$root.projectNamesList = this.projectNames;  // Store project names in the root instance for reuse
          this.$root.projectsLoaded = true;  // Mark project names as loaded
        } else {
          console.error('API response is not an array:', response.data);
        }
      } catch (error) {
        console.error('Error fetching projects:', error);
      }
    },
    async submitNewTRE() {
      try {
        const requestPayload = {
          user: this.newTRE.user,
          project: this.newTRE.project,
          memory: this.newTRE.memory,
          storage: this.newTRE.storage,
          gpu: this.newTRE.gpu,
          name: this.newTRE.name,
          description: this.newTRE.description,
          owner: this.newTRE.owner,
        };

        const response = await axios.post('http://127.0.0.1:8000/request-new-environment', requestPayload);

        // Reset the form after submission
        this.newTRE = {
          project: '',
          name: '',
          description: '',
          memory: 0,
          storage: 0,
          gpu: '',
          owner: '',
          user: '',
        };
        this.formExpanded = false;

        // Optionally, you can refresh the TRE list
        this.fetchTREs();
      } catch (error) {
        console.error('Error submitting new TRE:', error.response.data);
      }
    },
  },
};
</script>

<style scoped>
.transparent-text {
  background-color: transparent !important;
  padding: 16px; /* Adjust padding if necessary */
}
.hovered-button {
  min-width: 150px; /* Adjust the width as needed */
  justify-content: center;
}
.plain-text {
  font-size: 16px;
  font-weight: bold;
  padding-left: 8px; /* Optional: add some padding for better alignment */
}
.project-select {
  max-width: 400px; /* Adjust to control the width of the dropdown */
}
</style>
