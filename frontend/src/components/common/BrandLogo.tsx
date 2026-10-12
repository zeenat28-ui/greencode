import React from 'react';

interface BrandLogoProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const SIZE_MAP = {
  sm: 'w-7 h-7 rounded-lg',
  md: 'w-9 h-9 rounded-xl',
  lg: 'w-11 h-11 rounded-xl',
};

export default function BrandLogo({ size = 'md', className = '' }: BrandLogoProps) {
  return (
    <img
      src="/logo.png"
      alt="GreenCode"
      className={`${SIZE_MAP[size]} object-contain select-none shrink-0 shadow-xs ring-1 ring-emerald-950/10 ${className}`}
    />
  );
}

