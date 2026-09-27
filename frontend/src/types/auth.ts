export type Role = 'ADMIN' | 'WARD_STAFF' | 'COLLECTOR' | 'TREATMENT_FACILITY' | 'REGULATOR';

export type User = {
  id: number;
  name: string;
  email: string;
  role: Role;
  facility_id: number | null;
  ward_id: number | null;
  status: string;
  facility_name?: string | null;
  ward_name?: string | null;
};

export type AuthState = {
  token: string | null;
  user: User | null;
};
