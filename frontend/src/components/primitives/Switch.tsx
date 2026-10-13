import { useId, useState } from 'react';
import { cn } from '../../lib/utils';

export interface SwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  description?: string;
  size?: 'sm' | 'md';
  disabled?: boolean;
}

export function Switch({ checked, onChange, label, description, size = 'md', disabled = false }: SwitchProps) {
  const id = useId();
  const sizes = {
    sm: { track: 'w-10 h-5', thumb: 'w-4 h-4', translate: 'translate-x-5' },
    md: { track: 'w-12 h-6', thumb: 'w-5 h-5', translate: 'translate-x-6' },
  };
  const s = sizes[size];

  return (
    <div className="flex items-start gap-2.5 cursor-pointer" onClick={() => !disabled && onChange(!checked)}>
      <div className="pt-0.5 flex flex-col flex-1">
        {label && <span className="text-sm font-medium text-zinc-900 block">{label}</span>}
        {description && <span className="text-[11px] text-zinc-500">{description}</span>}
      </div>
      <label htmlFor={id} className="cursor-pointer" aria-label="toggle">
        <input
          id={id}
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          disabled={disabled}
          className="sr-only"
          aria-checked={checked}
        />
        <div
          className={cn(
            'relative inline-block transition-colors duration-200 rounded-full',
            s.track,
            checked ? 'bg-emerald-600' : 'bg-zinc-300',
            disabled && 'opacity-50 cursor-not-allowed'
          )}
        >
          <span
            className={cn(
              'absolute top-0.5 left-0.5 h-full w-0.5 rounded-full bg-white shadow transition-transform duration-200',
              s.thumb,
              checked && s.translate,
              !checked && 'translate-x-0'
            )}
          />
        </div>
      </label>
    </div>
  );
}
