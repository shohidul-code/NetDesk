import { Link } from "react-router";
import { PageHeader } from "@/components/states";
import { Button } from "@/components/ui/button";
import { BillsCard } from "@/features/customer-home/BillsCard";
import { ConnectionCard } from "@/features/customer-home/ConnectionCard";
import { LatestComplaint } from "@/features/customer-home/LatestComplaint";
import { NoticeBanner } from "@/features/customer-home/NoticeBanner";

export function CustomerHomePage() {
  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <PageHeader title="Home" />
      <NoticeBanner />
      <ConnectionCard />
      <BillsCard />
      <LatestComplaint />
      <Button asChild className="h-11 w-full">
        <Link to="/assistant">Ask the assistant</Link>
      </Button>
    </div>
  );
}
