import { Link } from "react-router";
import { Button } from "@/components/ui/button";

export function NotFoundPage() {
  return (
    <div className="mx-auto mt-16 max-w-md space-y-4 text-center">
      <h1 className="text-2xl font-semibold">Page not found</h1>
      <p className="text-text-muted">This address does not exist.</p>
      <Button asChild>
        <Link to="/">Go to my home</Link>
      </Button>
    </div>
  );
}
