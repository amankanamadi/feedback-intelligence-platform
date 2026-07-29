export type Role = "USER" | "ADMIN";

export type Me = {
  id: number;
  email: string;
  full_name: string | null;
  role: Role;
  is_active: boolean;
  created_at: string;
};
