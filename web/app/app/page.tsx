"use client";

import Link from "next/link";
import { BarChart3, MessageSquareHeart, MessageSquarePlus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/lib/auth";
import { STAFF_ROLES } from "@/types/auth";

export default function AppHomePage() {
  const { user } = useAuth();
  const isStaff = !!user && STAFF_ROLES.includes(user.role);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Welcome back</h1>
        <p className="text-muted-foreground">
          {isStaff
            ? "Review incoming guest and host feedback, monitor operational analytics, and manage cases."
            : "Share a review, report an issue with your stay or listing, or check in on feedback you've already shared."}
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <MessageSquarePlus className="size-8 text-primary" aria-hidden="true" />
            <CardTitle>Submit new feedback</CardTitle>
            <CardDescription>Share a review, report an issue, or tell us how we&apos;re doing.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild>
              <Link href="/app/feedback/new">Submit feedback</Link>
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <MessageSquareHeart className="size-8 text-primary" aria-hidden="true" />
            <CardTitle>{isStaff ? "Feedback queue" : "Track your feedback"}</CardTitle>
            <CardDescription>
              {isStaff
                ? "Review, categorize, and respond to incoming guest and host feedback."
                : "See the status and any responses on what you've already sent."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="outline" asChild>
              <Link href="/app/feedback">{isStaff ? "Go to feedback" : "View my feedback"}</Link>
            </Button>
          </CardContent>
        </Card>
        {isStaff && (
          <Card>
            <CardHeader>
              <BarChart3 className="size-8 text-primary" aria-hidden="true" />
              <CardTitle>Analytics</CardTitle>
              <CardDescription>Sentiment, properties, cities, and trends across all guest and host feedback.</CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="outline" asChild>
                <Link href="/app/analytics">View analytics</Link>
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
