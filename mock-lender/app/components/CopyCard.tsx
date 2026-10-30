import type { ReceivedCopyRowSelect } from "@/app/lib/db/schema";
import { formatDateTime } from "./format";

type CopyCardProps = {
  // Every column except the XML bytes.
  copy: Omit<ReceivedCopyRowSelect, "xml">;
  // The grant this copy came from no longer gives access.
  accessEnded: boolean;
};

const CopyCard = ({ copy, accessEnded }: CopyCardProps) => {
  return (
    <div className="card card-border bg-base-100">
      <div className="card-body">
        <div className="flex items-center justify-between">
          <h3 className="card-title">Grant {copy.grantId}</h3>
          {/* A copy is only stored when its hash matched both core's header
              and the hash listed with the grant. */}
          <span className="badge badge-success">SHA-256 verified</span>
        </div>

        <div className="text-sm">
          <div>Received {formatDateTime(copy.fetchedAt.toISOString())}</div>
          <div title={copy.sha256}>
            SHA-256{" "}
            <span className="font-mono">{copy.sha256.slice(0, 12)}…</span>
          </div>
        </div>

        {/* L-01: revocation stops future fetches, not copies already held. */}
        {accessEnded && (
          <div role="note" className="alert alert-info text-sm">
            Access to this application has ended, but this lender still holds
            the copy it fetched earlier.
          </div>
        )}
      </div>
    </div>
  );
};

export default CopyCard;
