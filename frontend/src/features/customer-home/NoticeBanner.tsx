import { Megaphone } from "lucide-react";
import { useActiveNotices } from "./queries";

/** Active notices for the customer's area. Quiet when loading, empty or failed: it is extra news, not the page. */
export function NoticeBanner() {
  const notices = useActiveNotices();
  if (!notices.data?.length) return null;
  return (
    <section aria-label="Notices" className="space-y-2">
      {notices.data.map((n) => (
        <div key={n.id} className="flex gap-3 rounded-lg border border-warning/40 bg-warning/10 p-3">
          <Megaphone className="mt-0.5 size-5 shrink-0 text-warning" aria-hidden />
          <div>
            <p className="font-medium text-warning">{n.kind === "outage" ? "Outage" : "Maintenance"}</p>
            <p>{n.message_bn}</p>
            <p className="text-sm text-text-muted">{n.message_en}</p>
          </div>
        </div>
      ))}
    </section>
  );
}
