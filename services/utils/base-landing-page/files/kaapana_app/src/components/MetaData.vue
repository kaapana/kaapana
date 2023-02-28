<template>
  <v-card>
    <v-card-title>
      <v-container align-items="center">
        <v-row align="center" justify="center">
          <v-col>
            <v-row align="center" justify="center">
              Patients
            </v-row>
            <v-row align="center" justify="center">
              {{ this.metaData['Patient ID'] && this.metaData['Patient ID']['items'].length || 'N/A' }}
            </v-row>
          </v-col>
          <v-col>
            <v-row align="center" justify="center">
              Studies
            </v-row>
            <v-row align="center" justify="center">
              {{ this.metaData['Study Instance UID'] && this.metaData['Study Instance UID']['items'].length || 'N/A' }}
            </v-row>
          </v-col>
          <v-col>
            <v-row align="center" justify="center">
              Series
            </v-row>
            <v-row align="center" justify="center">
              {{
                this.metaData['Series Instance UID'] && this.metaData['Series Instance UID']['items'].length || 'N/A'
              }}
            </v-row>
          </v-col>
        </v-row>
      </v-container>
    </v-card-title>

    <v-card-text>
      <apexcharts
          v-for="[key, value] in Object.entries(this.metaData).filter(
                ([_key, _value]) => ['Modality', 'Patient Sex', 'Manufacturer', 'dataset tags'].includes(_key)
              )"
          :key="JSON.stringify({key: value})"
          :options="{
            chart: {
              id: key,
              events: {
                dataPointSelection: (event, chartContext, config) => {
                  return dataPointSelection(event, chartContext, config, key, value)
                },
              },
              toolbar: {
                show: true,
                offsetX: 0,
                offsetY: 0,
                tools: {
                  download: true,
                  selection: true,
                  zoom: true,
                  zoomin: true,
                  zoomout: true,
                  pan: true,
                  reset: true,
                  //customIcons: []
                },
                export: {
                  csv: {
                    filename: undefined,
                    columnDelimiter: ',',
                    headerCategory: 'category',
                    headerValue: 'value',
                    dateFormatter(timestamp) {
                      return new Date(timestamp).toDateString()
                    }
                  },
                  svg: {
                    filename: undefined,
                  },
                  png: {
                    filename: undefined,
                  }
                },
                autoSelected: 'zoom'
              },
            },
            title: {
              text: key,
            },
            xaxis: {
              categories: value['items'].map(item => item['value']),
              tickPlacement: 'on'
            }
          }"
          :series="[{
            name: key,
            data: value['items'].map(item => item.count)
          }]"
          type="bar"
      >
      </apexcharts>
    </v-card-text>
  </v-card>
</template>

<script>
/* eslint-disable */
import VueApexCharts from "vue-apexcharts";


export default {
  name: 'MetaData',
  components: {
    apexcharts: VueApexCharts,
  },
  props: {
    metaData: {
      type: Object,
      default: {}
    }
  },
  data() {
    return {};
  },
  methods: {
    dataPointSelection(event, chartContext, config, key, value) {
      this.$emit(
          'dataPointSelection',
          {
            key: key,
            value: value['items'].map(item => item['value'])[config['dataPointIndex']]
          }
      )
    }
  }
};
</script>
<style scoped>
</style>
