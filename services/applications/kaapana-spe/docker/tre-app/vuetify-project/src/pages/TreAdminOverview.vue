<template>
    <v-container>
      <!-- Open User Requests Headline -->
      <v-row>
        <v-col>
          <h2>Open User Requests</h2>
        </v-col>
      </v-row>
  
      <!-- Open User Requests Section -->
      <v-row>
        <v-col>
          <v-card>
            <v-card-text>
              <v-radio-group v-model="selectedRequestId" @change="showRequestDetails">
                <v-radio
                  v-for="request in requests"
                  :key="request.id"
                  :label="`TRE request ${request.id} (${request.user})`"
                  :value="request.id"
                ></v-radio>
              </v-radio-group>
            </v-card-text>
          </v-card>
        </v-col>
  
        <v-col>
          <v-card v-if="selectedRequest">
            <v-card-title>
              Request Details
            </v-card-title>
            <v-card-text>
              <div v-for="(value, key) in selectedRequest" :key="key">
                <p><strong>{{ formatKey(key) }}:</strong> {{ value }}</p>
              </div>
            </v-card-text>
            <v-card-actions>
              <v-btn color="success" @click="answerRequest(true)">Approve</v-btn>
              <v-btn color="error" @click="answerRequest(false)">Deny</v-btn>
            </v-card-actions>
          </v-card>
          <v-card v-else>
            <v-card-text>Select a request to view details</v-card-text>
          </v-card>
        </v-col>
      </v-row>
  
      <!-- Currently Running TREs Section -->
      <v-row>
        <v-col>
          <h2>TRE Overview</h2>
        </v-col>
      </v-row>
  
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
    </v-container>
  </template>
  
  <script>
  import axios from 'axios';
  
  export default {
    data() {
      return {
        requests: [],
        selectedRequestId: null,
        selectedRequest: null,
        tres: [
          {
            name: "TRE 1",
            link: "https://example.com/tre1",
            expanded: false,
            details: "Detailed information about TRE 1.",
          },
          {
            name: "TRE 2",
            link: "https://example.com/tre2",
            expanded: false,
            details: "Detailed information about TRE 2.",
          },
        ],
      };
    },
    created() {
      this.fetchRequests();
      this.fetchTREs();

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
      async fetchEnvironments() {
        try {
          const response = await axios.get('http://127.0.0.1:8000/api/environments');
          this.requests = response.data;
        } catch (error) {
          console.error('Error fetching requests:', error);
        }
      },
      async fetchRequests() {
        try {
          const response = await axios.get('http://127.0.0.1:8000/api/requests');
          this.requests = response.data;
        } catch (error) {
          console.error('Error fetching requests:', error);
        }
      },
      showRequestDetails() {
        this.selectedRequest = this.requests.find(
          (request) => request.id === this.selectedRequestId
        );
      },
      async answerRequest(isAccepted) {
    if (this.selectedRequest) {
        try {
            const response = await axios.post(`http://127.0.0.1:8000/api/answer-request`, null, {
                params: {
                    request_id: this.selectedRequest.id,
                    is_accepted: isAccepted
                }
            });
            alert(
              `Request from ${this.selectedRequest.user} has been ${
                isAccepted ? "approved" : "denied"
              }.`
            );
            // await this.removeRequest(this.selectedRequest.id);
            await this.fetchRequests();
        } catch (error) {
            console.error(
              `Error ${isAccepted ? "approving" : "denying"} request:`,
              error
            );
            alert(
              `There was an error ${
                isAccepted ? "approving" : "denying"
              } the request.`
            );
        }
    }
}
,
      async removeRequest(requestId) {
        try {
          await axios.delete(`http://127.0.0.1:8000/api/requests/${requestId}`);
          this.requests = this.requests.filter(
            (request) => request.id !== requestId
          );
          this.selectedRequest = null;
          this.selectedRequestId = null;
        } catch (error) {
          console.error('Error deleting request:', error);
        }
      },
      formatKey(key) {
        return key.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase());
      },
    },
  };
  </script>
  
  <style scoped>
  .v-container {
    margin-top: 20px;
  }
  .v-card {
    margin: 10px;
  }
  .transparent-text {
    background-color: transparent !important;
    padding: 16px;
  }
  .plain-text {
    font-size: 16px;
    font-weight: bold;
    padding-left: 8px;
  }
  </style>
  