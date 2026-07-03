import React from 'react';
import type { Representation, Segmentation } from './contexts';

type ColorValue = string | number[] | undefined | null;

const getFirstSegmentIndex = (segments?: Record<number, unknown>) => {
  if (!segments) {
    return;
  }

  const firstSegment = Object.values(segments).find(Boolean) as
    | { segmentIndex?: number }
    | undefined;
  const firstKey = Object.keys(segments)[0];
  const segmentIndex = Number(firstSegment?.segmentIndex ?? firstKey);

  return Number.isFinite(segmentIndex) ? segmentIndex : undefined;
};

const colorToCss = (color: ColorValue) => {
  if (!color) {
    return;
  }

  if (typeof color === 'string') {
    return color;
  }

  if (color.length < 3) {
    return;
  }

  const [r, g, b] = color;
  if (![r, g, b].every(Number.isFinite)) {
    return;
  }

  return `rgb(${Math.round(r)},${Math.round(g)},${Math.round(b)})`;
};

const _loggedSwatchColors = new Set<string>();

export const getSegmentationDisplayColor = (
  segmentation?: Segmentation,
  representation?: Representation
) => {
  const segmentIndex =
    getFirstSegmentIndex(representation?.segments) ?? getFirstSegmentIndex(segmentation?.segments);

  if (segmentIndex === undefined) {
    return;
  }

  const representationSegment = representation?.segments?.[segmentIndex] as any;
  const segmentationSegment = segmentation?.segments?.[segmentIndex] as any;

  const css = colorToCss(
    representationSegment?.color ??
      segmentationSegment?.color ??
      representationSegment?.cachedStats?.color ??
      segmentationSegment?.cachedStats?.color
  );

  const logKey = `${segmentation?.segmentationId ?? '?'}:${css ?? 'none'}`;
  if (!_loggedSwatchColors.has(logKey)) {
    _loggedSwatchColors.add(logKey);
    console.debug(
      `[nninter/dbg] swatch: ${segmentation?.label ?? '?'} (${segmentation?.segmentationId ?? '?'}) → ${css ?? 'NO COLOR RESOLVED'}`
    );
  }

  return css;
};

export const SegmentationColorSwatch = ({
  color,
  className = '',
}: {
  color?: string;
  className?: string;
}) => {
  if (!color) {
    return null;
  }

  // Geometry/border via INLINE styles, not Tailwind: the app ships only ui-next's precompiled CSS,
  // and classes this extension uses exist only if ui-next happens to use them too (h-2.5/w-2.5 and
  // the border/ring opacity classes are NOT in ohif-ui-next.css → the swatch rendered zero-sized
  // and invisible). Inline styles cannot be purged.
  return (
    <span
      aria-hidden="true"
      className={className}
      style={{
        display: 'inline-block',
        width: 10,
        height: 10,
        flexShrink: 0,
        borderRadius: '50%',
        backgroundColor: color,
        border: '1px solid rgba(0,0,0,0.5)',
        boxShadow: '0 0 0 1px rgba(255,255,255,0.35)',
      }}
    />
  );
};
