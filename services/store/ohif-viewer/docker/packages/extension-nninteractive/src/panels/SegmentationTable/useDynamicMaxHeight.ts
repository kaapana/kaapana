import { RefObject, useEffect, useRef, useState } from 'react';

export function useDynamicMaxHeight(
  data: any,
  buffer = 20,
  minHeight = 100
): {
  ref: RefObject<HTMLDivElement>;
  maxHeight: string;
} {
  const ref = useRef<HTMLDivElement>(null);
  const [maxHeight, setMaxHeight] = useState<string>('100vh');

  useEffect(() => {
    const calculateMaxHeight = () => {
      if (!ref.current) {
        return;
      }

      const rect = ref.current.getBoundingClientRect();
      const availableHeight = window.innerHeight - rect.top - buffer;
      setMaxHeight(`${Math.max(minHeight, availableHeight)}px`);
    };

    const rafId = requestAnimationFrame(calculateMaxHeight);
    window.addEventListener('resize', calculateMaxHeight);

    return () => {
      window.removeEventListener('resize', calculateMaxHeight);
      cancelAnimationFrame(rafId);
    };
  }, [data, buffer, minHeight]);

  return { ref, maxHeight };
}
