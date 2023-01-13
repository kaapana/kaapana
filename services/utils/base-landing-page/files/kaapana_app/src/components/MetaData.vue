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
              {{ this.metaData && this.metaData['Patient Name keyword']['items'].length || 'N/A' }}
            </v-row>
          </v-col>
          <v-col>
            <v-row align="center" justify="center">
              Studies
            </v-row>
            <v-row align="center" justify="center">
              {{ this.metaData && this.metaData['Study Instance UID']['items'].length || 'N/A' }}
            </v-row>
          </v-col>
          <v-col>
            <v-row align="center" justify="center">
              Series
            </v-row>
            <v-row align="center" justify="center">
              {{ this.metaData && this.metaData['Series Instance UID']['items'].length || 'N/A' }}
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
              // selection: {
              //   enabled: true
              // },
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
                  reset: true ,
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
            // theme: {
            //       mode: 'dark',
            //       // palette: 'palette1',
            //       // monochrome: {
            //       //     enabled: false,
            //       //     color: '#255aee',
            //       //     shadeTo: 'light',
            //       //     shadeIntensity: 0.65
            //       // },
            //   },
            title: {
                text: key,
                // align: 'left',
                // margin: 10,
                // offsetX: 0,
                // offsetY: 0,
                // floating: false,
                // style: {
                //   fontSize:  '14px',
                //   fontWeight:  'bold',
                //   fontFamily:  undefined,
                //   color:  '#263238'
                // },
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
    return {
      // chartOptions: {
      //   chart: {
      //     id: "basic-bar",
      //     events: {
      //       dataPointSelection: (event, chartContext, config) => {
      //         console.log("event triggered");
      //         console.log(
      //             "index selected: ",
      //             config["seriesIndex"],
      //             config["dataPointIndex"]
      //         );
      //         console.log(
      //             config["w"]["config"]["xaxis"]["categories"][
      //                 config["dataPointIndex"]
      //                 ]
      //         );
      //         console.log(event, chartContext, config);
      //       },
      //     },
      //   },
      //   xaxis: {},
      // },
      // series: [],
    };
  },
};
</script>
<style scoped>
</style>
