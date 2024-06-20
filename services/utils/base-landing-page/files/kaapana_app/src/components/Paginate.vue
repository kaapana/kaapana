<template>
  <div :class="{'pagination-container': true, 'hidden': !showPagination}">
      <v-pagination 
        v-if="showPagination"
        :length="Math.ceil(aggregatedSeriesNum / pageLength)" 
        v-model="pageIndex">
      </v-pagination>
    </div>
  </template>

  <script>
  export default {
    props: {
      aggregatedSeriesNum: {
        type: Number,
        required: true
      },
      pageLength: {
        type: Number,
        required: true,  
        default: 1000
      }, 
    },
    data() {
      return {
        pageIndex: 1,
        showPagination: true,
        lastPage: 0,
        lastPageLength: 0
      };
    },
    watch: {
      pageLength() {
        this.updatePaginationVisibility();
        this.onPaginate();
      },
      aggregatedSeriesNum() {
        this.updatePaginationVisibility();
        //console.log('aggregatedSeriesNum:', this.pageIndex, this.pageLength, this.aggregatedSeriesNum);
        if(this.pageIndex * this.pageLength > this.aggregatedSeriesNum){
            this.pageIndex = 1;
        }

      },
      pageIndex() {
        this.$emit("onPageIndexChange", this.pageIndex)
        this.updatePaginationVisibility();
        this.onPaginate();
        //console.log('pageIndex:', this.pageIndex, this.pageLength, this.aggregatedSeriesNum);
      },
    },
    methods: {
      onPaginate() {
        //console.log('onPaginate:', this.pageIndex, this.pageLength);
        //only trigger on changes
        if (this.pageIndex != this.lastPage || this.pageLength != this.lastPageLength){
            this.$emit('updateData', {}, true);
        }
        this.lastPage = this.pageIndex;
        this.lastPageLength = this.pageLength;       
      },
      onPageLengthChange() {
        this.pageIndex = 1; // Reset to first page
        this.onPaginate(); 
      },
      updatePaginationVisibility() {
        this.showPagination = Math.ceil(this.aggregatedSeriesNum / this.pageLength) > 1;
        //console.log('updatePaginationVisibility:', this.showPagination);
      },
      getPageIndexAndLength() {
        return {
          pageIndex: this.pageIndex,
          pageLength: this.pageLength
        };
      },
    },
  };
  </script>
  
  <style scoped>
  .pagination-container {
    display: flex;
    align-items: center;
    margin: 0;
    padding: 0;
  }
  
  .pagination-container.hidden {
    display: none; /* Hide the container completely when pagination is not shown */
  }
  
  .v-pagination {
    padding: 0;
    margin: 0;
    height: auto;
  }
  </style>