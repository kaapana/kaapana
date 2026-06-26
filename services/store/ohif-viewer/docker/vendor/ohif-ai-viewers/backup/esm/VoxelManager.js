import cache from '../cache/cache';
import RLEVoxelMap from './RLEVoxelMap';
import isEqual from './isEqual';
import { iterateOverPointsInShapeVoxelManager } from './pointInShapeCallback';
const DEFAULT_RLE_SIZE = 5 * 1024;
export default class VoxelManager {
    get id() {
        return this._id;
    }
    constructor(dimensions, options) {
        this.modifiedSlices = new Set();
        this.boundsIJK = [
            [Infinity, -Infinity],
            [Infinity, -Infinity],
            [Infinity, -Infinity],
        ];
        this.scalarData = null;
        this._sliceDataCache = null;
        this.getAtIJK = (i, j, k) => {
            const index = this.toIndex([i, j, k]);
            return this._get(index);
        };
        this.setAtIJK = (i, j, k, v) => {
            const index = this.toIndex([i, j, k]);
            const changed = this._set(index, v);
            if (changed !== false) {
                this.modifiedSlices.add(k);
                VoxelManager.addBounds(this.boundsIJK, [i, j, k]);
            }
            return changed;
        };
        this.getAtIJKPoint = ([i, j, k]) => this.getAtIJK(i, j, k);
        this.setAtIJKPoint = ([i, j, k], v) => {
            this.setAtIJK(i, j, k, v);
        };
        this.getAtIndex = (index) => this._get(index);
        this.setAtIndex = (index, v) => {
            const changed = this._set(index, v);
            if (changed !== false) {
                const pointIJK = this.toIJK(index);
                this.modifiedSlices.add(pointIJK[2]);
                VoxelManager.addBounds(this.boundsIJK, pointIJK);
            }
            return changed;
        };
        this.getMiddleSliceData = () => {
            const middleSliceIndex = Math.floor(this.dimensions[2] / 2);
            return this.getSliceData({
                sliceIndex: middleSliceIndex,
                slicePlane: 2,
            });
        };
        this.forEach = (callback, options = {}) => {
            const isInObjectBoundsIJK = options.boundsIJK || this.getBoundsIJK();
            const isInObject = options.isInObject || this.isInObject || (() => true);
            const returnPoints = options.returnPoints || false;
            const useLPSTransform = options.imageData;
            const iMin = Math.min(isInObjectBoundsIJK[0][0], isInObjectBoundsIJK[0][1]);
            const iMax = Math.max(isInObjectBoundsIJK[0][0], isInObjectBoundsIJK[0][1]);
            const jMin = Math.min(isInObjectBoundsIJK[1][0], isInObjectBoundsIJK[1][1]);
            const jMax = Math.max(isInObjectBoundsIJK[1][0], isInObjectBoundsIJK[1][1]);
            const kMin = Math.min(isInObjectBoundsIJK[2][0], isInObjectBoundsIJK[2][1]);
            const kMax = Math.max(isInObjectBoundsIJK[2][0], isInObjectBoundsIJK[2][1]);
            const pointsInShape = [];
            if (useLPSTransform) {
                const pointsInShape = iterateOverPointsInShapeVoxelManager({
                    voxelManager: this,
                    imageData: options.imageData,
                    bounds: [
                        [iMin, iMax],
                        [jMin, jMax],
                        [kMin, kMax],
                    ],
                    pointInShapeFn: isInObject,
                    callback,
                    returnPoints,
                });
                return pointsInShape;
            }
            if (this.map) {
                if (this.map instanceof RLEVoxelMap) {
                    return this.rleForEach(callback, options);
                }
                for (const index of this.map.keys()) {
                    const pointIJK = this.toIJK(index);
                    if (!isInObject(null, pointIJK)) {
                        continue;
                    }
                    const value = this._get(index);
                    if (returnPoints) {
                        pointsInShape.push({
                            value,
                            index,
                            pointIJK,
                            pointLPS: null,
                        });
                    }
                    callback({ value, index, pointIJK, pointLPS: null });
                }
                return pointsInShape;
            }
            else {
                for (let k = kMin; k <= kMax; k++) {
                    const kIndex = k * this.frameSize;
                    for (let j = jMin; j <= jMax; j++) {
                        const jIndex = kIndex + j * this.width;
                        for (let i = iMin, index = jIndex + i; i <= iMax; i++, index++) {
                            const value = this.getAtIndex(index);
                            const pointIJK = [i, j, k];
                            if (!isInObject(null, pointIJK)) {
                                continue;
                            }
                            if (returnPoints) {
                                pointsInShape.push({
                                    value,
                                    index,
                                    pointIJK,
                                    pointLPS: null,
                                });
                            }
                            callback({ value, index, pointIJK: [i, j, k], pointLPS: null });
                        }
                    }
                }
                return pointsInShape;
            }
        };
        this.getSliceData = ({ sliceIndex, slicePlane, }) => {
            const [width, height, depth] = this.dimensions;
            const frameSize = width * height;
            const startIndex = sliceIndex * frameSize;
            let sliceSize;
            const SliceDataConstructor = this.getConstructor();
            function isValidConstructor(ctor) {
                return typeof ctor === 'function';
            }
            if (!isValidConstructor(SliceDataConstructor)) {
                return new Uint8Array(0);
            }
            let sliceData;
            switch (slicePlane) {
                case 0:
                    sliceSize = height * depth;
                    sliceData = new SliceDataConstructor(sliceSize);
                    for (let i = 0; i < height; i++) {
                        for (let j = 0; j < depth; j++) {
                            const index = sliceIndex + i * width + j * frameSize;
                            this.setSliceDataValue(sliceData, i * depth + j, this._get(index));
                        }
                    }
                    break;
                case 1:
                    sliceSize = width * depth;
                    sliceData = new SliceDataConstructor(sliceSize);
                    for (let i = 0; i < width; i++) {
                        for (let j = 0; j < depth; j++) {
                            const index = i + sliceIndex * width + j * frameSize;
                            this.setSliceDataValue(sliceData, i + j * width, this._get(index));
                        }
                    }
                    break;
                case 2:
                    sliceSize = width * height;
                    sliceData = new SliceDataConstructor(sliceSize);
                    for (let i = 0; i < sliceSize; i++) {
                        this.setSliceDataValue(sliceData, i, this._get(startIndex + i));
                    }
                    break;
                default:
                    throw new Error('Oblique plane - todo - implement as ortho normal vector');
            }
            return sliceData;
        };
        this.dimensions = dimensions;
        this.width = dimensions[0];
        this.frameSize = this.width * dimensions[1];
        this._get = options._get;
        this._set = options._set;
        this._id = options._id || '';
        this._getConstructor = options._getConstructor;
        this.numberOfComponents = this.numberOfComponents || 1;
        this.scalarData = options.scalarData;
        this._getScalarData = options._getScalarData;
        this._updateScalarData = options._updateScalarData;
    }
    getMinMax() {
        let min, max;
        const callback = ({ value: v }) => {
            const isArray = Array.isArray(v);
            if (min === undefined) {
                min = isArray ? [...v] : v;
                max = isArray ? [...v] : v;
            }
            if (isArray) {
                for (let i = 0; i < v.length; i++) {
                    min[i] = Math.min(min[i], v[i]);
                    max[i] = Math.max(max[i], v[i]);
                }
            }
            else {
                min = Math.min(min, v);
                max = Math.max(max, v);
            }
        };
        this.forEach(callback, { boundsIJK: this.getDefaultBounds() });
        return { min, max };
    }
    toIJK(index) {
        return [
            index % this.width,
            Math.floor((index % this.frameSize) / this.width),
            Math.floor(index / this.frameSize),
        ];
    }
    toIndex(ijk) {
        return ijk[0] + ijk[1] * this.width + ijk[2] * this.frameSize;
    }
    getDefaultBounds() {
        return this.dimensions.map((dimension) => [0, dimension - 1]);
    }
    getBoundsIJK() {
        if (this.boundsIJK[0][0] < this.dimensions[0]) {
            return this.boundsIJK;
        }
        return this.getDefaultBounds();
    }
    rleForEach(callback, options) {
        const boundsIJK = options?.boundsIJK || this.getBoundsIJK();
        const { isWithinObject } = options || {};
        const map = this.map;
        if (!map) {
            console.warn('No map found, you need to use a map voxel manager to use rleForEach');
            return;
        }
        map.defaultValue = undefined;
        for (let k = boundsIJK[2][0]; k <= boundsIJK[2][1]; k++) {
            for (let j = boundsIJK[1][0]; j <= boundsIJK[1][1]; j++) {
                const row = map.getRun(j, k);
                if (!row) {
                    continue;
                }
                for (const rle of row) {
                    const { start, end, value } = rle;
                    const baseIndex = this.toIndex([0, j, k]);
                    for (let i = start; i < end; i++) {
                        const callbackArguments = {
                            value,
                            index: baseIndex + i,
                            pointIJK: [i, j, k],
                        };
                        if (isWithinObject?.(callbackArguments) === false) {
                            continue;
                        }
                        callback(callbackArguments);
                    }
                }
            }
        }
    }
    getScalarData(storeScalarData = false) {
        if (this.scalarData) {
            this._updateScalarData?.(this.scalarData);
            return this.scalarData;
        }
        if (this._getScalarData) {
            const scalarData = this._getScalarData();
            if (storeScalarData) {
                console.log('Not transient, should store value', scalarData);
            }
            return scalarData;
        }
        throw new Error('No scalar data available');
    }
    setScalarData(newScalarData) {
        this.scalarData = newScalarData;
    }
    getScalarDataLength() {
        if (this.scalarData) {
            return this.scalarData.length;
        }
        if (this._getScalarDataLength) {
            return this._getScalarDataLength();
        }
        throw new Error('No scalar data available');
    }
    get sizeInBytes() {
        return this.getScalarDataLength() * this.bytePerVoxel;
    }
    get bytePerVoxel() {
        if (this.scalarData) {
            return this.scalarData.BYTES_PER_ELEMENT;
        }
        const value = this._get(0);
        return value.BYTES_PER_ELEMENT;
    }
    clearBounds() {
        this.boundsIJK.map((bound) => {
            bound[0] = Infinity;
            bound[1] = -Infinity;
        });
    }
    clear() {
        this.map?.clear();
        this.clearBounds();
        this.modifiedSlices.clear();
        this.points?.clear();
    }
    getConstructor() {
        if (this.scalarData) {
            return this.scalarData.constructor;
        }
        if (this._getConstructor) {
            return this._getConstructor();
        }
        console.warn('No scalar data available or can be used to get the constructor');
        return Float32Array;
    }
    getArrayOfModifiedSlices() {
        return Array.from(this.modifiedSlices);
    }
    resetModifiedSlices() {
        this.modifiedSlices.clear();
    }
    setBounds(bounds) {
        this.boundsIJK = bounds;
    }
    static addBounds(bounds, point) {
        if (!bounds) {
            bounds = [
                [Infinity, -Infinity],
                [Infinity, -Infinity],
                [Infinity, -Infinity],
            ];
        }
        bounds[0][0] = Math.min(point[0], bounds[0][0]);
        bounds[0][1] = Math.max(point[0], bounds[0][1]);
        bounds[1][0] = Math.min(point[1], bounds[1][0]);
        bounds[1][1] = Math.max(point[1], bounds[1][1]);
        bounds[2][0] = Math.min(point[2], bounds[2][0]);
        bounds[2][1] = Math.max(point[2], bounds[2][1]);
    }
    addPoint(point) {
        const index = Array.isArray(point)
            ? point[0] + this.width * point[1] + this.frameSize * point[2]
            : point;
        if (!this.points) {
            this.points = new Set();
        }
        this.points.add(index);
    }
    getPoints() {
        return this.points
            ? [...this.points].map((index) => this.toIJK(index))
            : [];
    }
    setSliceDataValue(sliceData, index, value) {
        if (Array.isArray(value)) {
            for (let i = 0; i < value.length; i++) {
                sliceData[index * value.length + i] = this.toNumber(value[i]);
            }
        }
        else {
            sliceData[index] = this.toNumber(value);
        }
    }
    toNumber(value) {
        if (typeof value === 'number') {
            return value;
        }
        if (Array.isArray(value)) {
            return value[0] || 0;
        }
        return 0;
    }
    static _createRGBScalarVolumeVoxelManager({ dimensions, scalarData, numberOfComponents = 3, id, }) {
        const voxels = new VoxelManager(dimensions, {
            _get: (index) => {
                index *= numberOfComponents;
                return [
                    scalarData[index++],
                    scalarData[index++],
                    scalarData[index++],
                ];
            },
            _id: id || '_createRGBScalarVolumeVoxelManager',
            _set: (index, v) => {
                index *= 3;
                const isChanged = !isEqual(scalarData[index], v);
                scalarData[index++] = v[0];
                scalarData[index++] = v[1];
                scalarData[index++] = v[2];
                return isChanged;
            },
            numberOfComponents,
            scalarData,
        });
        voxels.clear = () => {
            scalarData.fill(0);
        };
        return voxels;
    }
    static createImageVolumeVoxelManager({ dimensions, imageIds, numberOfComponents = 1, id, }) {
        const pixelsPerSlice = dimensions[0] * dimensions[1];
        function getPixelInfo(index) {
            const sliceIndex = Math.floor(index / pixelsPerSlice);
            if (sliceIndex < 0 || sliceIndex >= dimensions[2]) {
                return {};
            }
            const imageId = imageIds[sliceIndex];
            if (!imageId) {
                console.warn(`ImageId not found for sliceIndex: ${sliceIndex}`);
                return { pixelData: null, pixelIndex: null };
            }
            const image = cache.getImage(imageId);
            if (!image) {
                console.warn(`Image not found for imageId: ${imageId}`);
                return { pixelData: null, pixelIndex: null };
            }
            const voxelManager = image.voxelManager;
            const pixelIndex = index % pixelsPerSlice;
            return { voxelManager, pixelIndex };
        }
        function getVoxelValue(index) {
            const { voxelManager: imageVoxelManager, pixelIndex } = getPixelInfo(index);
            if (!imageVoxelManager || pixelIndex === null) {
                return null;
            }
            return imageVoxelManager.getAtIndex(pixelIndex);
        }
        function setVoxelValue(index, v) {
            const { voxelManager: imageVoxelManager, pixelIndex } = getPixelInfo(index);
            if (!imageVoxelManager || pixelIndex === null) {
                return false;
            }
            const currentValue = imageVoxelManager.getAtIndex(pixelIndex);
            const isChanged = !isEqual(v, currentValue);
            if (!isChanged) {
                return isChanged;
            }
            imageVoxelManager.setAtIndex(pixelIndex, v);
            return true;
        }

        // Helper function to find the first cached image's voxelManager
        // Cached for reuse across multiple calls
        let cachedFirstImageVoxelManager = null;
        const getFirstCachedImageVoxelManager = () => {
        if (cachedFirstImageVoxelManager !== null) {
            return cachedFirstImageVoxelManager;
        }
        // Find the first cached image to get its voxelManager
        // Don't rely on index 0 which may not be cached yet
        for (let i = 0; i < imageIds.length; i++) {
            const imageId = imageIds[i];
            if (!imageId) {
            continue;
            }
            const image = cache.getImage(imageId);
            if (image && image.voxelManager) {
            cachedFirstImageVoxelManager = image.voxelManager;
            return cachedFirstImageVoxelManager;
            }
        }
        return null;
        };

        const _getConstructor = () => {
            const firstVoxelManager = getFirstCachedImageVoxelManager();
            if (!firstVoxelManager) {
                return null;
            }
            return firstVoxelManager.getConstructor();
        };
        const voxelManager = new VoxelManager(dimensions, {
            _get: getVoxelValue,
            _set: setVoxelValue,
            numberOfComponents,
            _getConstructor,
            _id: id || 'createImageVolumeVoxelManager',
        });
        // Should return imageIds which is used to create this voxel manager
        voxelManager.getImageIds = () => {
            if (imageIds.length > 0 && imageIds[0].startsWith('derived:')) {
            //segmentation imageIds, find referenced imageIds
            const referencedImageIds = imageIds.map(imageId => {
                const image = cache.getImage(imageId);
                return image.referencedImageId;
            });
            return referencedImageIds;
            }
            return imageIds;
        };
        voxelManager.getMiddleSliceData = () => {
            const middleSliceIndex = Math.floor(dimensions[2] / 2);
            return voxelManager.getSliceData({
                sliceIndex: middleSliceIndex,
                slicePlane: 2,
            });
        };
        voxelManager.clear = () => {
            for (const imageId of imageIds) {
                const image = cache.getImage(imageId);
                image.voxelManager.clear();
            }
        };
        voxelManager.getRange = () => {
            let minValue = Infinity;
            let maxValue = -Infinity;
            for (const imageId of imageIds) {
                const image = cache.getImage(imageId);
                if (!image) {
                    continue;
                }
                if (image.minPixelValue < minValue) {
                    minValue = image.minPixelValue;
                }
                if (image.maxPixelValue > maxValue) {
                    maxValue = image.maxPixelValue;
                }
            }
            if (minValue === Infinity && maxValue === -Infinity) {
                return [0, 0];
            }
            return [minValue, maxValue];
        };
        voxelManager._getScalarDataLength = () => {
            const firstVoxelManager = getFirstCachedImageVoxelManager();
            if (!firstVoxelManager) {
                return 0;
            }
            return firstVoxelManager.getScalarDataLength() * dimensions[2];
        };
        voxelManager.getCompleteScalarDataArray = () => {
            const ScalarDataConstructor = voxelManager._getConstructor();
            if (!ScalarDataConstructor) {
                return new Uint8Array(0);
            }
            const dataLength = voxelManager.getScalarDataLength();
            const scalarData = new ScalarDataConstructor(dataLength);
            const sliceSize = dimensions[0] * dimensions[1] * numberOfComponents;
            for (let sliceIndex = 0; sliceIndex < dimensions[2]; sliceIndex++) {
                const { voxelManager: imageVoxelManager, pixelIndex } = getPixelInfo((sliceIndex * sliceSize) / numberOfComponents);
                if (imageVoxelManager && pixelIndex !== null) {
                    const sliceStart = sliceIndex * sliceSize;
                    const pixelData = imageVoxelManager.getScalarData();
                    if (numberOfComponents === 1) {
                        scalarData.set(pixelData, sliceStart);
                    }
                    else {
                        for (let i = 0; i < pixelData.length; i += numberOfComponents) {
                            for (let j = 0; j < numberOfComponents; j++) {
                                scalarData[sliceStart + i + j] = pixelData[i + j];
                            }
                        }
                    }
                }
            }
            return scalarData;
        };
        voxelManager.setCompleteScalarDataArray = (scalarData) => {
            const sliceSize = dimensions[0] * dimensions[1] * numberOfComponents;
            const SliceDataConstructor = voxelManager._getConstructor();
            let minValue = Infinity;
            let maxValue = -Infinity;
            for (let sliceIndex = 0; sliceIndex < dimensions[2]; sliceIndex++) {
                const { voxelManager: imageVoxelManager } = getPixelInfo((sliceIndex * sliceSize) / numberOfComponents);
                if (imageVoxelManager && SliceDataConstructor) {
                    const sliceStart = sliceIndex * sliceSize;
                    const sliceEnd = sliceStart + sliceSize;
                    const sliceData = new SliceDataConstructor(sliceSize);
                    sliceData.set(scalarData.subarray(sliceStart, sliceEnd));
                    if (imageVoxelManager.scalarData) {
                        imageVoxelManager.scalarData.set(sliceData);
                        imageVoxelManager.modifiedSlices.add(sliceIndex);
                    }
                    else {
                        for (let i = 0; i < sliceSize; i++) {
                            imageVoxelManager.setAtIndex(i, sliceData[i]);
                        }
                    }
                    for (let i = 0; i < sliceData.length; i++) {
                        const value = sliceData[i];
                        minValue = Math.min(minValue, value);
                        maxValue = Math.max(maxValue, value);
                    }
                    const imageId = imageIds[sliceIndex];
                    const image = cache.getImage(imageId);
                    if (image) {
                        image.minPixelValue = minValue;
                        image.maxPixelValue = maxValue;
                    }
                }
            }
            for (let k = 0; k < dimensions[2]; k++) {
                voxelManager.modifiedSlices.add(k);
            }
            voxelManager.boundsIJK = [
                [0, dimensions[0] - 1],
                [0, dimensions[1] - 1],
                [0, dimensions[2] - 1],
            ];
        };
        return voxelManager;
    }
    static createScalarVolumeVoxelManager({ dimensions, scalarData, numberOfComponents, id, }) {
        if (dimensions.length !== 3) {
            throw new Error('Dimensions must be provided as [number, number, number] for [width, height, depth]');
        }
        if (!numberOfComponents) {
            numberOfComponents =
                scalarData.length / dimensions[0] / dimensions[1] / dimensions[2];
            if (numberOfComponents > 4 ||
                numberOfComponents < 1 ||
                numberOfComponents === 2) {
                throw new Error(`Number of components ${numberOfComponents} must be 1, 3 or 4`);
            }
        }
        if (numberOfComponents > 1) {
            return VoxelManager._createRGBScalarVolumeVoxelManager({
                dimensions,
                scalarData,
                numberOfComponents,
                id,
            });
        }
        return VoxelManager._createNumberVolumeVoxelManager({
            dimensions,
            scalarData,
            id,
        });
    }
    static createScalarDynamicVolumeVoxelManager({ imageIdGroups, dimensions, dimensionGroupNumber = 1, timePoint = 0, numberOfComponents = 1, id, }) {
        let activeDimensionGroup = 0;
        if (dimensionGroupNumber !== undefined) {
            activeDimensionGroup = dimensionGroupNumber - 1;
        }
        else if (timePoint !== undefined) {
            console.warn('Warning: timePoint parameter is deprecated. Please use dimensionGroupNumber instead. timePoint is zero-based while dimensionGroupNumber starts at 1.');
            activeDimensionGroup = timePoint;
        }
        if (!numberOfComponents) {
            const firstImage = cache.getImage(imageIdGroups[0][0]);
            if (!firstImage) {
                throw new Error('Unable to determine number of components: No image found');
            }
            numberOfComponents =
                firstImage.getPixelData().length / (dimensions[0] * dimensions[1]);
            if (numberOfComponents > 4 ||
                numberOfComponents < 1 ||
                numberOfComponents === 2) {
                throw new Error(`Number of components ${numberOfComponents} must be 1, 3 or 4`);
            }
        }
        const voxelGroups = imageIdGroups.map((imageIds) => {
            return VoxelManager.createImageVolumeVoxelManager({
                dimensions,
                imageIds,
                numberOfComponents,
                id,
            });
        });
        const voxelManager = new VoxelManager(dimensions, {
            _get: (index) => voxelGroups[activeDimensionGroup]._get(index),
            _set: (index, v) => voxelGroups[activeDimensionGroup]._set(index, v),
            numberOfComponents,
            _id: id || 'createScalarDynamicVolumeVoxelManager',
        });
        voxelManager.getScalarDataLength = () => {
            return voxelGroups[activeDimensionGroup].getScalarDataLength();
        };
        voxelManager.getConstructor = () => {
            return voxelGroups[activeDimensionGroup].getConstructor();
        };
        voxelManager.getRange = () => {
            return voxelGroups[activeDimensionGroup].getRange();
        };
        voxelManager.getMiddleSliceData = () => {
            return voxelGroups[activeDimensionGroup].getMiddleSliceData();
        };
        voxelManager.setTimePoint = (newTimePoint) => {
            console.warn('Warning: setTimePoint is deprecated. Please use setDimensionGroupNumber instead. Note that timePoint is zero-based while dimensionGroupNumber starts at 1.');
            voxelManager.setDimensionGroupNumber(newTimePoint + 1);
        };
        voxelManager.setDimensionGroupNumber = (newDimensionGroupNumber) => {
            activeDimensionGroup = newDimensionGroupNumber - 1;
            voxelManager._get = (index) => voxelGroups[activeDimensionGroup]._get(index);
            voxelManager._set = (index, v) => voxelGroups[activeDimensionGroup]._set(index, v);
        };
        voxelManager.getAtIndexAndTimePoint = (index, tp) => {
            console.warn('Warning: getAtIndexAndTimePoint is deprecated. Please use getAtIndexAndDimensionGroup instead. Note that timePoint is zero-based while dimensionGroupNumber starts at 1.');
            return voxelManager.getAtIndexAndDimensionGroup(index, tp + 1);
        };
        voxelManager.getAtIndexAndDimensionGroup = (index, dimensionGroupNumber) => {
            return voxelGroups[dimensionGroupNumber - 1]._get(index);
        };
        voxelManager.getTimePointScalarData = (tp) => {
            console.warn('Warning: getTimePointScalarData is deprecated. Please use getDimensionGroupScalarData instead. Note that timePoint is zero-based while dimensionGroupNumber starts at 1.');
            return voxelManager.getDimensionGroupScalarData(tp + 1);
        };
        voxelManager.getDimensionGroupScalarData = (dimensionGroupNumber) => {
            return voxelGroups[dimensionGroupNumber - 1].getCompleteScalarDataArray();
        };
        voxelManager.getCurrentTimePointScalarData = () => {
            console.warn('Warning: getCurrentTimePointScalarData is deprecated. Please use getCurrentDimensionGroupScalarData instead.');
            return voxelManager.getCurrentDimensionGroupScalarData();
        };
        voxelManager.getCurrentDimensionGroupScalarData = () => {
            return voxelGroups[activeDimensionGroup].getCompleteScalarDataArray();
        };
        voxelManager.getCurrentTimePoint = () => {
            console.warn('Warning: getCurrentTimePoint is deprecated. Please use getCurrentDimensionGroupNumber instead. Note that timePoint is zero-based while dimensionGroupNumber starts at 1.');
            return activeDimensionGroup;
        };
        voxelManager.getCurrentDimensionGroupNumber = () => {
            return activeDimensionGroup + 1;
        };
        return voxelManager;
    }
    static createImageVoxelManager({ width, height, scalarData, numberOfComponents = 1, id, }) {
        const dimensions = [width, height, 1];
        if (!numberOfComponents) {
            numberOfComponents = scalarData.length / width / height;
            if (numberOfComponents > 4 ||
                numberOfComponents < 1 ||
                numberOfComponents === 2) {
                throw new Error(`Number of components ${numberOfComponents} must be 1, 3 or 4`);
            }
        }
        if (numberOfComponents > 1) {
            return VoxelManager._createRGBScalarVolumeVoxelManager({
                dimensions,
                scalarData,
                numberOfComponents,
                id,
            });
        }
        return VoxelManager._createNumberVolumeVoxelManager({
            dimensions,
            scalarData,
            id,
        });
    }
    static _createNumberVolumeVoxelManager({ dimensions, scalarData, id, }) {
        const voxels = new VoxelManager(dimensions, {
            _get: (index) => scalarData[index],
            _set: (index, v) => {
                const isChanged = scalarData[index] !== v;
                scalarData[index] = v;
                return isChanged;
            },
            _getConstructor: () => scalarData.constructor,
            _id: id || '_createNumberVolumeVoxelManager',
        });
        voxels.scalarData = scalarData;
        voxels.clear = () => {
            voxels.scalarData.fill(0);
        };
        voxels.getMiddleSliceData = () => {
            const middleSliceIndex = Math.floor(dimensions[2] / 2);
            return voxels.getSliceData({
                sliceIndex: middleSliceIndex,
                slicePlane: 2,
            });
        };
        return voxels;
    }
    static createMapVoxelManager({ dimension, id, }) {
        const map = new Map();
        const voxelManager = new VoxelManager(dimension, {
            _get: map.get.bind(map),
            _set: (index, v) => map.set(index, v) && true,
            _id: id || 'createMapVoxelManager',
        });
        voxelManager.map = map;
        return voxelManager;
    }
    static createHistoryVoxelManager(sourceVoxelManager, id) {
        const map = new Map();
        const { dimensions } = sourceVoxelManager;
        const voxelManager = new VoxelManager(dimensions, {
            _get: (index) => map.get(index),
            _set: function (index, v) {
                if (!map.has(index)) {
                    const oldV = this.sourceVoxelManager.getAtIndex(index);
                    if (oldV === v) {
                        return false;
                    }
                    map.set(index, oldV);
                }
                else if (v === map.get(index)) {
                    map.delete(index);
                }
                this.sourceVoxelManager.setAtIndex(index, v);
            },
            _id: id || 'createHistoryVoxelManager',
        });
        voxelManager.map = map;
        voxelManager.scalarData = sourceVoxelManager.scalarData;
        voxelManager.sourceVoxelManager = sourceVoxelManager;
        return voxelManager;
    }
    static createRLEHistoryVoxelManager(sourceVoxelManager, id) {
        const { dimensions } = sourceVoxelManager;
        const map = new RLEVoxelMap(dimensions[0], dimensions[1], dimensions[2]);
        const voxelManager = new VoxelManager(dimensions, {
            _get: (index) => map.get(index),
            _set: function (index, v) {
                const originalV = map.get(index);
                if (originalV === undefined) {
                    const oldV = this.sourceVoxelManager.getAtIndex(index);
                    if (oldV === v || (oldV === undefined && v === 0) || v === null) {
                        return false;
                    }
                    map.set(index, oldV ?? 0);
                }
                else if (v === originalV || v === null) {
                    map.delete(index);
                    v = originalV;
                }
                this.sourceVoxelManager.setAtIndex(index, v);
            },
            _getScalarData: RLEVoxelMap.getScalarData,
            _updateScalarData: (scalarData) => {
                map.updateScalarData(scalarData);
                return scalarData;
            },
            _id: id || 'createRLEHistoryVoxelManager',
        });
        voxelManager.map = map;
        voxelManager.sourceVoxelManager = sourceVoxelManager;
        return voxelManager;
    }
    static createLazyVoxelManager({ dimensions, planeFactory, id, }) {
        const map = new Map();
        const [width, height] = dimensions;
        const planeSize = width * height;
        const voxelManager = new VoxelManager(dimensions, {
            _get: (index) => map.get(Math.floor(index / planeSize))[index % planeSize],
            _set: (index, v) => {
                const k = Math.floor(index / planeSize);
                let layer = map.get(k);
                if (!layer) {
                    layer = planeFactory(width, height);
                    map.set(k, layer);
                }
                layer[index % planeSize] = v;
                return true;
            },
            _id: id || 'createLazyVoxelManager',
        });
        voxelManager.map = map;
        return voxelManager;
    }
    static createRLEVolumeVoxelManager({ dimensions, id, }) {
        const [width, height, depth] = dimensions;
        const map = new RLEVoxelMap(width, height, depth);
        const voxelManager = new VoxelManager(dimensions, {
            _get: (index) => map.get(index),
            _set: (index, v) => {
                map.set(index, v);
                return true;
            },
            _getScalarData: RLEVoxelMap.getScalarData,
            _updateScalarData: (scalarData) => {
                map.updateScalarData(scalarData);
                return scalarData;
            },
            _id: id || 'createRLEVolumeVoxelManager',
        });
        voxelManager.map = map;
        voxelManager.getPixelData = map.getPixelData.bind(map);
        return voxelManager;
    }
    static createRLEImageVoxelManager({ dimensions, id, }) {
        const [width, height] = dimensions;
        return VoxelManager.createRLEVolumeVoxelManager({
            dimensions: [width, height, 1],
            id,
        });
    }
    static addInstanceToImage(image) {
        const { width, height } = image;
        const scalarData = image.voxelManager.getScalarData();
        if (scalarData.length >= width * height) {
            image.voxelManager = VoxelManager.createScalarVolumeVoxelManager({
                dimensions: [width, height, 1],
                scalarData,
            });
            return;
        }
        image.voxelManager = VoxelManager.createRLEVolumeVoxelManager({
            dimensions: [width, height, 1],
        });
        image.getPixelData = image.voxelManager.getPixelData;
        image.sizeInBytes = DEFAULT_RLE_SIZE;
    }
}
