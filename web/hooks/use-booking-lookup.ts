import { useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { BookingRead } from "@/types/booking";

export function useBookingLookupMutation() {
  return useMutation({
    mutationFn: (confirmationCode: string) =>
      apiFetch<BookingRead>(`/bookings/${encodeURIComponent(confirmationCode.trim())}`),
  });
}
