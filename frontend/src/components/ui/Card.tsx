import type { ReactNode } from 'react';

type CardProps = {
  children: ReactNode;
  className?: string;
};

export function Card({ children, className = '' }: CardProps) {
  return <div className={`rounded-xl border border-slate-200 bg-white p-5 shadow-soft ${className}`}>{children}</div>;
}
