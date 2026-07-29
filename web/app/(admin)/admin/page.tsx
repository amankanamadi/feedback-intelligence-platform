import { BarChart3, Inbox } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function AdminHomePage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Admin Console</h1>
        <p className="text-muted-foreground">Manage feedback, review AI insights, and monitor analytics.</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <Inbox className="size-8 text-primary" aria-hidden="true" />
            <CardTitle>Feedback queue</CardTitle>
            <CardDescription>Review, categorize, and respond to incoming feedback.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild>
              <Link href="/admin/feedback">Go to feedback</Link>
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <BarChart3 className="size-8 text-primary" aria-hidden="true" />
            <CardTitle>Analytics</CardTitle>
            <CardDescription>Sentiment, categories, and trends across all feedback.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="outline" asChild>
              <Link href="/admin/analytics">View analytics</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
