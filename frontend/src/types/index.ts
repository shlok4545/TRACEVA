export type Role = 'admin' | 'ward_staff' | 'collector' | 'treatment_facility' | 'regulator';

export type Metric = {
  label: string;
  value: string;
  change?: string;
  tone?: 'default' | 'success' | 'warning' | 'danger';
};

export type NavItem = {
  label: string;
  to: string;
  icon?: string;
};

export type StatusTone = 'success' | 'warning' | 'danger' | 'neutral' | 'info';
