<template>
    <div class="variable-list">
      <div class="tables-container">
        <div class="variables-table">
          <div
            class="variable-row"
            v-for="(variable, index) in variables"
            :key="index"
            @click="selectVariable(index)"
            :class="{ 'selected': index === selectedVariableIndex }"
          >
            <div class="variable-info">
              <div class="variable-name">{{ variable.name }}</div>
              <div class="variable-value">{{ variable.value }}</div>
            </div>
          </div>
        </div>
  
  
      <div class="selected-description" v-if="selectedVariableIndex !== null">
        {{ descriptions[selectedVariableIndex].text }}
      </div>
    </div>
  </div>
  </template>
  
  <script>
  export default {
    data() {
      return {
        variables: [
          { name: 'Variable 1', value: 'Value 1' },
          { name: 'Variable 2', value: 'Value 2' },
          { name: 'Variable 3', value: 'Value 3' },
          // Add more variables as needed
        ],
        descriptions: [
          { name: 'Description 1', text: 'This is the first description.' },
          { name: 'Description 2', text: 'This is the second description.\n It can have multiple lines.' },
          { name: 'Description 3', text: 'This is the third description.' },
          // Add more descriptions as needed
        ],
        selectedVariableIndex: null,
        selectedDescriptionIndex: null,
      };
    },
    methods: {
      selectVariable(index) {
        this.selectedVariableIndex = index;
        this.selectedDescriptionIndex = null;
      },
      selectDescription(index) {
        this.selectedDescriptionIndex = index;
        this.selectedVariableIndex = null;
      },
    },
  };
  </script>
  
  <style scoped>
  .variable-list {
    border: 1px solid #ccc;
    padding: 10px;
    margin: 10px;
  }
  
  .tables-container {
    display: flex;
    justify-content: space-between;
  }
  
  .variables-table {
    flex: 1;
  }
  
  .variable-row {
    display: flex;
    align-items: center;
    padding: 5px 0;
    border-bottom: 1px solid #ddd;
    cursor: pointer;
  }
  
  .variable-row.selected {
    background-color: #f0f0f0;
  }
  
  .variable-info {
    display: flex;
    align-items: center;
  }
  
  .variable-name {
    font-weight: bold;
    margin-right: 10px;
  }
  
  .variable-value {
    margin-right: 10px;
  }
  
  .descriptions-table {
    flex: 1;
    margin-left: 20px;
  }
  
  .description-row {
    display: flex;
    align-items: center;
    padding: 5px 0;
    border-bottom: 1px solid #ddd;
    cursor: pointer;
  }
  
  .description-row.selected {
    background-color: #f0f0f0;
  }
  
  .description-name {
    font-weight: bold;
    margin-right: 10px;
  }
  
  .selected-description {
    background-color: #f0f0f0;
    padding: 10px;
    border: 1px solid #ccc;
    margin-top: 10px;
  }
  </style>