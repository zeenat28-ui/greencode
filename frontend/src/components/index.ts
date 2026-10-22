/* ================================================================
   Primitives — shared building blocks for the design system
   ================================================================ */
export { Button } from './primitives/Button';
export type { ButtonProps, ButtonVariant, ButtonSize } from './primitives/Button';

export { Input } from './primitives/Input';
export type { InputProps } from './primitives/Input';

export { Select } from './primitives/Select';
export type { SelectProps } from './primitives/Select';

export { Textarea } from './primitives/Textarea';
export type { TextareaProps } from './primitives/Textarea';

export { Badge } from './primitives/Badge';
export type { BadgeProps, BadgeVariant, BadgeSize } from './primitives/Badge';
export { badgeVariants } from './primitives/Badge';

export { Card, CardHeader, CardTitle, CardDescription, CardContent } from './primitives/Card';
export type { CardProps, CardVariant, CardPadding } from './primitives/Card';

export { Modal } from './primitives/Modal';
export type { ModalProps } from './primitives/Modal';

export { DataTable } from './primitives/DataTable';
export type { ColumnDef, DataTableProps, ColumnAlign } from './primitives/DataTable';

export { EmptyState } from './primitives/EmptyState';
export type { EmptyStateProps } from './primitives/EmptyState';

export { ErrorState } from './primitives/ErrorState';
export type { ErrorStateProps } from './primitives/ErrorState';

export { LoadingState } from './primitives/LoadingState';
export type { LoadingStateProps, LoadingStateVariant } from './primitives/LoadingState';

export { PageHeader } from './primitives/PageHeader';
export type { PageHeaderProps } from './primitives/PageHeader';

export { StatCard } from './primitives/StatCard';
export type { StatCardProps } from './primitives/StatCard';

export { ProgressRing } from './primitives/ProgressRing';
export type { ProgressRingProps, ProgressVariant, ProgressSize } from './primitives/ProgressRing';

export { Checkbox } from './primitives/Checkbox';
export type { CheckboxProps } from './primitives/Checkbox';

export { Switch } from './primitives/Switch';
export type { SwitchProps } from './primitives/Switch';

export { Tabs, TabList, Tab, TabPanel } from './primitives/Tabs';
export type { TabsProps, TabListProps, TabProps, TabPanelProps } from './primitives/Tabs';

/* ================================================================
   Layouts
   ================================================================ */
export { default as AppLayout } from './layouts/AppLayout';
export { default as ProtectedRoute } from './layouts/ProtectedRoute';
export { default as Navbar } from './layouts/Navbar';
export { default as Sidebar } from './layouts/Sidebar';

/* ================================================================
   Common Components
   ================================================================ */
export { default as BrandLogo } from './common/BrandLogo';
export { default as ScoreBadge } from './common/ScoreBadge';
export { default as MetricCard } from './common/MetricCard';
export { default as SeverityPill, IssueCard } from './common/IssueCard';
export { default as CodeDiffViewer } from './common/CodeDiffViewer';
export { default as ErrorBoundary } from './common/ErrorBoundary';
export { default as AlexaVoiceCockpit } from './common/AlexaVoiceCockpit';
export { default as EsgAuditModal } from './common/EsgAuditModal';
export { default as CiCdBadgeModal } from './common/CiCdBadgeModal';
export { default as FinOpsCalculatorModal } from './common/FinOpsCalculatorModal';
export { default as GitHubBotPreviewModal } from './common/GitHubBotPreviewModal';
export { default as AmazonTechStackModal } from './common/AmazonTechStackModal';

/* ================================================================
   Charts
   ================================================================ */
export { default as ViolationChart } from './charts/ViolationChart';
export { LanguageChart, ScoreGauge } from './charts/ViolationChart';

export { default as TenantSwitcher } from './primitives/TenantSwitcher';
export { default as ThemeToggle } from './primitives/ThemeToggle';
