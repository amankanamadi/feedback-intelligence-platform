import type { Property } from "@/types/feedback";

export type WishlistRead = {
  id: number;
  created_at: string;
  property: Property;
};
