import React from 'react';
import type { IconProps } from '../types';

const iconClassName = (className?: string) =>
  ['h-[24px] w-[24px]', className].filter(Boolean).join(' ');

export const ToolNnInteractivePoint = ({ className, ...props }: IconProps) => (
  <svg
    {...props}
    className={iconClassName(className)}
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 256 256"
  >
    <circle fill="currentColor" cx="145.71" cy="56.89" r="21.26" />
    <circle fill="currentColor" cx="73.29" cy="94.08" r="21.26" />
    <circle fill="currentColor" cx="188.55" cy="120.06" r="21.26" />
    <circle fill="currentColor" cx="145.71" cy="183.24" r="21.26" />
    <circle fill="currentColor" cx="65.92" cy="187.32" r="21.26" />
  </svg>
);

export const ToolNnInteractiveBbox = ({ className, ...props }: IconProps) => (
  <svg
    {...props}
    className={iconClassName(className)}
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 256 256"
  >
    <path
      fill="currentColor"
      d="M198.37,170.81v-85.62c7.19-3.28,12.2-10.52,12.2-18.95,0-11.49-9.32-20.82-20.82-20.82-8.42,0-15.67,5.01-18.95,12.2h-85.62c-3.28-7.19-10.52-12.2-18.95-12.2-11.49,0-20.82,9.32-20.82,20.82,0,8.42,5.01,15.67,12.2,18.95v85.62c-7.19,3.28-12.2,10.52-12.2,18.95,0,11.49,9.32,20.82,20.82,20.82,8.42,0,15.67-5.01,18.95-12.2h85.62c3.28,7.19,10.52,12.2,18.95,12.2,11.49,0,20.82-9.32,20.82-20.82,0-8.42-5.01-15.67-12.2-18.95h0ZM74.86,170.81v-85.62c4.57-2.08,8.25-5.76,10.33-10.33h85.62c2.08,4.57,5.76,8.25,10.33,10.33v85.62c-4.57,2.08-8.25,5.76-10.33,10.33h-85.62c-2.08-4.57-5.76-8.25-10.33-10.33Z"
    />
  </svg>
);

export const ToolNnInteractiveScribble = ({ className, ...props }: IconProps) => (
  <svg
    {...props}
    className={iconClassName(className)}
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 256 256"
  >
    <path
      fill="none"
      stroke="currentColor"
      strokeMiterlimit={10}
      strokeWidth={24}
      d="M59.75,140.72c14.34-42.38,34.59-92,52.44-89.97,6.08.69,9.88,7.14,12.85,12.34,26.5,46.36-21.31,105.81,2.96,130.07,5.19,5.19,12.7,7.78,19.15,7.35,22.68-1.53,42.84-41.13,51.41-100.92"
    />
  </svg>
);

export const ToolNnInteractiveLasso = ({ className, ...props }: IconProps) => (
  <svg
    {...props}
    className={iconClassName(className)}
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 256 256"
  >
    <path
      fill="currentColor"
      d="M224.88,65c0-12.15-9.85-22-22-22-8.07,0-15.11,4.34-18.94,10.81l-85.4,4.9c-3.58-7.31-11.08-12.34-19.76-12.34-12.15,0-22,9.85-22,22,0,7.8,4.07,14.64,10.18,18.55l-19.51,78.29c-10.39,1.76-18.31,10.8-18.31,21.68,0,12.15,9.85,22,22,22s22-9.85,22-22c0-1.82-.23-3.59-.64-5.28l41.63-24.03c3.37,2.11,7.36,3.33,11.63,3.33,3.23,0,6.29-.7,9.06-1.95l19.9,23.96c-.94,2.46-1.47,5.11-1.47,7.9,0,12.15,9.85,22,22,22s22-9.85,22-22c0-7.22-3.48-13.63-8.85-17.64l18.71-86.6c10.13-1.97,17.78-10.89,17.78-21.59l.02.02h-.03ZM167.33,170.29l-20.59-24.79c.65-2.08,1.01-4.29,1.01-6.59,0-12.15-9.85-22-22-22s-22,9.85-22,22c0,1.34.13,2.65.36,3.93l-38.27,22.1,18.77-75.35c6.68-1.84,12.08-6.74,14.61-13.11l82.71-4.75c1.41,4.41,4.19,8.22,7.82,10.93l-18.7,86.57c-1.28.24-2.53.61-3.72,1.07h0Z"
    />
  </svg>
);
