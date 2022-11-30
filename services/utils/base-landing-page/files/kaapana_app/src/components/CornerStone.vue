<template>
  <div class="parent">
    <div ref="canvas" class="cover" oncontextmenu="return false"/>
    <div v-if="loading" class="cover overlay">
      <v-row
        class="fill-height ma-0"
        align="center"
        justify="center"
      >
        <v-progress-circular
          indeterminate
          color="primary"
        />
      </v-row>
    </div>
  </div>
</template>

<script>
/* eslint-disable */

// Packages
import * as cornerstone from "cornerstone-core";
import * as dicomParser from "dicom-parser";

import * as cornerstoneWADOImageLoader from "cornerstone-wado-image-loader";

import Hammer from "hammerjs";
import * as cornerstoneMath from "cornerstone-math";
import * as cornerstoneTools from "cornerstone-tools";
import * as dcmjs from "../static/dist/dcmjs";
import {loadDicom, loadSeriesMetaData} from "../common/api.service.js";

cornerstoneTools.external.Hammer = Hammer;
cornerstoneTools.external.cornerstone = cornerstone;
cornerstoneTools.external.cornerstoneMath = cornerstoneMath;

cornerstoneTools.init();

cornerstoneWADOImageLoader.external.cornerstoneMath = cornerstoneMath;
cornerstoneWADOImageLoader.external.dicomParser = dicomParser;
cornerstoneWADOImageLoader.external.cornerstone = cornerstone;

const config = {
  taskConfiguration: {
    decodeTask: {
      loadCodecsOnStartup: true,
      initializeCodecsOnStartup: false,
      codecsPath: "../static/dist/cornerstoneWADOImageLoaderCodecs.js",
      usePDFJS: false,
      strict: false
    }
  }
};
cornerstoneWADOImageLoader.webWorkerManager.initialize(config);

const metaData = {}

function metaDataProvider(type, imageId) {
  if (!metaData[imageId]) {
    return;
  }

  return metaData[imageId][type];
}

cornerstone.metaData.addProvider(metaDataProvider);

function addMetaData(type, imageId, data) {
  metaData[imageId] = metaData[imageId] || {};
  metaData[imageId][type] = data;
}


export default {
  name: "CornerStone",
  props: {
    seriesInstanceUID: {
      type: String,
    },
    studyInstanceUID: {
      type: String,
    },
  },
  data() {
    return {
      loading: true
    }
  },
  methods: {
    async load_segmentations(instance) {
      const element = this.canvas
      const arrayBuffer = await loadDicom(
        instance.studyInstanceUID,
        instance.seriesInstanceUID,
        instance.objectUID
      )

      const stackToolState = cornerstoneTools.getToolState(
        element,
        "stack"
      );
      const imageIds_ = stackToolState.data[0].imageIds;

      const {
        labelmapBufferArray,
        segMetadata,
        segmentsOnFrame
      } = dcmjs.adapters.Cornerstone.Segmentation.generateToolState(
        imageIds_,
        arrayBuffer,
        cornerstone.metaData,
      );

      const {setters, state} = cornerstoneTools.getModule(
        "segmentation"
      );

      setters.labelmap3DByFirstImageId(
        imageIds_[0],
        labelmapBufferArray[0],
        0,
        segMetadata,
        imageIds_.length,
        segmentsOnFrame
      );
      if (this.loading)
        this.loading = false
    },
    async load_data() {
      if (!this.loading)
        this.loading = true

      const seriesMetaData = await loadSeriesMetaData(
        this.studyInstanceUID,
        this.seriesInstanceUID
      )
      const isSegmentation = seriesMetaData.modality === 'SEG'
      let imageMetaData = seriesMetaData
      if (isSegmentation) {
        // selected item is a segmentation object
        imageMetaData = await loadSeriesMetaData(
          seriesMetaData.studyInstanceUID,
          seriesMetaData.referenceSeriesInstanceUID
        )
      }

      const imageIds = imageMetaData.imageIds

      const stack = {
        currentImageIdIndex: Math.floor(imageIds.length / 2),
        imageIds
      }

      const image = await cornerstone.loadAndCacheImage(imageIds[stack.currentImageIdIndex])

      const viewport = cornerstone.getDefaultViewportForImage(
        this.canvas,
        image
      );
      cornerstone.displayImage(this.canvas, image, viewport);
      cornerstoneTools.addStackStateManager(this.canvas, ['stack'])
      cornerstoneTools.addToolState(this.canvas, 'stack', stack)

      const imagePromises = imageIds.map(imageId => {
        return cornerstone.loadAndCacheImage(imageId);
      });

      Promise.all(imagePromises).then(() => {
        if (!isSegmentation)
          if (this.loading) {
            this.loading = false
            console.log('loading set to false')
          }
      });

      if (isSegmentation) {
        this.load_segmentations(seriesMetaData);
      }
      cornerstoneTools.addTool(cornerstoneTools.StackScrollMouseWheelTool)
      cornerstoneTools.addTool(cornerstoneTools.ZoomTool)
      cornerstoneTools.addTool(cornerstoneTools.WwwcTool)

      cornerstoneTools.setToolActive('StackScrollMouseWheel', {})
      cornerstoneTools.setToolActive("Zoom", {mouseButtonMask: 2}); // Right
      cornerstoneTools.setToolActive("Wwwc", {mouseButtonMask: 1}); // Left & Touch
    }
  },
  updated() {
  },
  created() {

  },
  async mounted() {
    if (!this.loading)
      this.loading = true
    console.log('cornerstone mounted')
    cornerstoneTools.init({
      globalToolSyncEnabled: true
    });
    // Enable Canvas
    this.canvas = this.$refs.canvas;
    cornerstone.enable(this.canvas, {
      renderer: "webgl"
    });
    this.load_data();
  },
  watch: {
    seriesInstanceUID() {
      console.log('watch seriesInstanceUID')
      this.load_data();
    },
    loading() {
      console.log(`loading: ${this.loading}`)
    },
  },
};
</script>

<style>
.parent {
  position: relative;
  height: 300px;
  width: 100%;
}

.cover {
  position: absolute;
  height: 100%;
  width: 100%;
  display: block;
}

.overlay {
  background: rgba(255, 255, 255, .5);
}
</style>
