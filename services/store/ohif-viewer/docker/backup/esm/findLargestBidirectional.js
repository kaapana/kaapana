import { vec3 } from 'gl-matrix';
import { createIsInSegment, isLineInSegment } from './isLineInSegment';
const thetaTol = (5 * Math.PI) / 180;
const EPSILON = 1e-2;
export default function findLargestBidirectional(contours, segVolumeId, segment) {
    const { sliceContours } = contours;
    const { segmentIndex, containedSegmentIndices } = segment;
    let maxBidirectional;
    const isInSegment = createIsInSegment(segVolumeId, segmentIndex, containedSegmentIndices);
    for (const sliceContour of sliceContours) {
        const bidirectional = createBidirectionalForSlice(sliceContour, isInSegment, maxBidirectional);
        if (!bidirectional) {
            continue;
        }
        maxBidirectional = bidirectional;
    }
    if (maxBidirectional) {
        Object.assign(maxBidirectional, segment);
    }
    return maxBidirectional;
}
export function createBidirectionalForSlice(
    sliceContour,
    isInSegment,
    currentMax = { maxMajor: 0, maxMinor: 0 }
  ) {
    const { points } = sliceContour.polyData;
    const { sliceIndex } = sliceContour;
    const { maxMinor: currentMaxMinor, maxMajor: currentMaxMajor } = currentMax;
    let maxMajor = currentMaxMajor ** 2;
    let maxMinor = currentMaxMinor ** 2;
    let areaMax = maxMajor * maxMinor;
    let maxMajorPoints;
    let maxMinorPoints;
    for (let major_index1 = 0; major_index1 < points.length; major_index1++) {
      for (let major_index2 = major_index1 + 1; major_index2 < points.length; major_index2++) {
        const major_point1 = points[major_index1];
        const major_point2 = points[major_index2];
        const major_distance2 = vec3.sqrDist(major_point1, major_point2);
        if (major_distance2 < maxMajor) {
          continue;
        }
        if (major_distance2 - EPSILON < maxMajor + EPSILON && maxMajorPoints) {
          // Consider adding to the set of points rather than continuing here
          // so that all minor axis can be tested
          continue;
        }
     
        maxMajor = major_distance2;
        maxMajorPoints = [major_index1, major_index2];
        areaMax = maxMajor * maxMinor;
      }
    }
    if (!maxMajorPoints) {
      return;
    }
    const handle0 = points[maxMajorPoints[0]];
    const handle1 = points[maxMajorPoints[1]];
    const unitMajor = vec3.sub(vec3.create(), handle0, handle1);
    vec3.scale(unitMajor, unitMajor, 1 / Math.sqrt(maxMajor));
    for (let minor_index1 = 0; minor_index1 < points.length; minor_index1++) {
      for (let minor_index2 = minor_index1 + 1; minor_index2 < points.length; minor_index2++) {
        const minor_point1 = points[minor_index1];
        const minor_point2 = points[minor_index2];
        const minor_distance2 = vec3.sqrDist(minor_point1, minor_point2);
        if (minor_distance2 * maxMajor < areaMax) {
          //pass, already smaller than current max area
          continue;
        }
        const delta = vec3.sub(vec3.create(), minor_point1, minor_point2);
        const dot = Math.abs(vec3.dot(delta, unitMajor)) / Math.sqrt(minor_distance2);
        if (dot > Math.cos(Math.PI / 2 - thetaTol)) {
          //pass, not perpendicular to major axis
          continue;
        }
        const wouldBeat = minor_distance2 * maxMajor > areaMax;
        if (wouldBeat) {
          maxMinor = minor_distance2;
          maxMinorPoints = [minor_index1, minor_index2];
          areaMax = maxMajor * maxMinor;
        }
      }
    }
  
    if (!maxMinorPoints || !maxMajorPoints) {
      return;
    }
  
    const handle2 = points[maxMinorPoints[0]];
    const handle3 = points[maxMinorPoints[1]];
    const bidirectional = {
      sliceIndex: sliceIndex,
      majorAxis: [handle0, handle1],
      minorAxis: [handle2, handle3],
      maxMajor: Math.sqrt(maxMajor),
      maxMinor: Math.sqrt(maxMinor),
      ...sliceContour,
    };
    return bidirectional;
  }
