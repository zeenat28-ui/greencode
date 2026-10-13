import { createContext, useContext, useState, useEffect } from 'react';
import { cn } from '../../lib/utils';

interface TabsState {
  value: string;
  onChange: (v: string) => void;
}

const TabsContext = createContext<TabsState | null>(null);

export interface TabsProps {
  defaultValue?: string;
  value?: string;
  onValueChange?: (value: string) => void;
  children: React.ReactNode;
  className?: string;
}

export interface TabListProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export interface TabProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  value: string;
  children: React.ReactNode;
}

export interface TabPanelProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string;
  children: React.ReactNode;
}

function useTabsContext() {
  const ctx = useContext(TabsContext);
  if (!ctx) throw new Error('Tab/TabPanel must be used within Tabs');
  return ctx;
}

export function Tabs({ defaultValue, value: controlledValue, onValueChange, children, className }: TabsProps) {
  const [uncontrolledValue, setUncontrolledValue] = useState(defaultValue || '');
  const isControlled = controlledValue !== undefined;
  const currentValue = isControlled ? controlledValue! : uncontrolledValue;

  const onChange = (v: string) => {
    if (!isControlled) setUncontrolledValue(v);
    onValueChange?.(v);
  };

  return (
    <TabsContext.Provider value={{ value: currentValue, onChange }}>
      <div className={cn('flex flex-col', className)}>{children}</div>
    </TabsContext.Provider>
  );
}

export function TabList({ className, children, ...props }: TabListProps) {
  return (
    <div
      className={cn(
        'flex items-center gap-1 p-1 rounded-lg bg-zinc-100 border border-zinc-200/80 text-xs font-medium',
        className
      )}
      role="tablist"
      {...props}
    >
      {children}
    </div>
  );
}

export function Tab({ value, children, className, ...props }: TabProps) {
  const ctx = useTabsContext();
  const isActive = ctx.value === value;

  return (
    <button
      type="button"
      role="tab"
      aria-selected={isActive}
      className={cn(
        'px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150',
        isActive
          ? 'bg-white text-zinc-900 shadow-sm'
          : 'text-zinc-500 hover:text-zinc-800'
      )}
      onClick={() => ctx.onChange(value)}
      {...props}
    >
      {children}
    </button>
  );
}

export function TabPanel({ value, children, className, ...props }: TabPanelProps) {
  const ctx = useTabsContext();
  if (ctx.value !== value) return null;

  return (
    <div className={cn('pt-3', className)} {...props}>
      {children}
    </div>
  );
}
