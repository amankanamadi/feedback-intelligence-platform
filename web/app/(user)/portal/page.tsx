import Link from "next/link";
import { MessageSquarePlus, MessageSquareHeart } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function PortalHomePage() {
  return (
    <div className="flex flex-1 flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Welcome back</h1>
        <p className="text-muted-foreground">Tell us what&apos;s on your mind, or check in on feedback you&apos;ve already shared.</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <MessageSquarePlus className="size-8 text-primary" aria-hidden="true" />
            <CardTitle>Submit new feedback</CardTitle>
            <CardDescription>Share an idea, report a bug, or tell us how we&apos;re doing.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild>
              <Link href="/portal/feedback/new">Submit feedback</Link>
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <MessageSquareHeart className="size-8 text-primary" aria-hidden="true" />
            <CardTitle>Track your feedback</CardTitle>
            <CardDescription>See the status and any responses on what you&apos;ve already sent.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="outline" asChild>
              <Link href="/portal/feedback/history">View my feedback</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
