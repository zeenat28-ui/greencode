interface BrandLogoProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const SIZE_MAP = {
  sm: 'w-7 h-7',
  md: 'w-8 h-8',
  lg: 'w-10 h-10',
};

export default function BrandLogo({ size = 'md', className = '' }: BrandLogoProps) {
  return (
    <img
      src="/logo.png"
      alt="GreenCode"
      className={`${SIZE_MAP[size]} object-contain select-none shrink-0 ${className}`}
    />
  );
}

