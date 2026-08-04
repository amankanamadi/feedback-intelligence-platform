import type { Property } from "@/types/feedback";

export type BookingStatus = "Upcoming" | "Completed" | "Cancelled";

export type BookingRead = {
  id: number;
  confirmation_code: string;
  check_in_date: string;
  check_out_date: string;
  status: BookingStatus;
  property: Property;
};
