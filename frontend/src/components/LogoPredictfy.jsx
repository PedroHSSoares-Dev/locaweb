import React, { useId } from 'react';

export default function LogoPredictfy({ className, style, size, color }) {
  const sz = size ?? undefined;
  const col = color ?? 'currentColor';
  const maskId = `${useId().replace(/:/g, '')}-node-cutout`;

  return (
    <svg
      className={className}
      style={{ color: col, ...style }}
      xmlns="http://www.w3.org/2000/svg"
      viewBox="31 31 258 258"
      width={sz ?? '100%'}
      height={sz ?? '100%'}
    >
      <defs>
        <mask
          id={maskId}
          x="31"
          y="31"
          width="258"
          height="258"
          maskUnits="userSpaceOnUse"
          maskContentUnits="userSpaceOnUse"
          style={{ maskType: 'alpha' }}
        >
          <rect width="100%" height="100%" fill="white" />
          <circle cx="120" cy="140" r="20" fill="black" />
          <circle cx="170" cy="190" r="20" fill="black" />
          <circle cx="230" cy="100" r="20" fill="black" />
        </mask>
      </defs>

      <rect x="40" y="40" width="240" height="240" rx="45" stroke="currentColor" strokeWidth="18" fill="none" strokeLinejoin="round" />
      <path d="M 60 260 L 120 140 L 170 190 L 230 100" stroke="currentColor" strokeWidth="18" fill="none" strokeLinecap="round" strokeLinejoin="round" mask={`url(#${maskId})`} />
      
      <circle cx="120" cy="140" r="20" stroke="currentColor" strokeWidth="18" fill="none" />
      <circle cx="170" cy="190" r="20" stroke="currentColor" strokeWidth="18" fill="none" />
      <circle cx="230" cy="100" r="20" stroke="currentColor" strokeWidth="18" fill="none" />
    </svg>
  );
}
