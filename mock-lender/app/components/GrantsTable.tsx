import type { CoreGrantRowSelect } from "@/app/lib/db/schema";
import FetchButton from "./FetchButton";
import { formatDateTime } from "./format";

type Grant = CoreGrantRowSelect;

// What the last fetch attempt got back from core.
const FETCH_RESULT: Record<
  NonNullable<Grant["lastFetchStatus"]>,
  { label: string; badge: string }
> = {
  ok: { label: "Fetched", badge: "badge-success" },
  access_ended: { label: "Access ended (404)", badge: "badge-neutral" },
  hash_mismatch: { label: "Hash mismatch", badge: "badge-error" },
  error: { label: "Error", badge: "badge-warning" },
};

const GrantRow = ({ clientId, grant }: { clientId: string; grant: Grant }) => {
  const result = grant.lastFetchStatus && FETCH_RESULT[grant.lastFetchStatus];

  return (
    <tr>
      <td className="font-mono">{grant.grantId}</td>
      <td>
        {/* core doesn't say why access ended: a revoked grant and an expired
            one both just stop being listed (ADR 0003). */}
        {grant.accessEndedAt ? (
          <div className="flex flex-col gap-1">
            <span className="badge badge-sm badge-neutral">access ended</span>
            <span className="text-xs opacity-70">
              {formatDateTime(grant.accessEndedAt.toISOString())}
            </span>
          </div>
        ) : (
          <span className="badge badge-sm badge-success">active</span>
        )}
      </td>
      <td className="text-sm">
        {formatDateTime(grant.expiresAt.toISOString())}
      </td>
      <td>
        {result && grant.lastFetchAttemptAt ? (
          <div className="flex flex-col gap-1">
            <span className={`badge badge-sm ${result.badge}`}>
              {result.label}
            </span>
            <span className="text-xs opacity-70">
              {formatDateTime(grant.lastFetchAttemptAt.toISOString())}
            </span>
          </div>
        ) : (
          <span className="text-sm opacity-70">Not fetched yet</span>
        )}
      </td>
      <td className="font-mono text-sm" title={grant.listedSha256}>
        {grant.listedSha256.slice(0, 12)}…
      </td>
      <td>
        <FetchButton clientId={clientId} grantId={grant.grantId} />
      </td>
    </tr>
  );
};

const GrantsTable = ({
  clientId,
  grants,
}: {
  clientId: string;
  grants: Grant[];
}) => {
  if (grants.length === 0) {
    return (
      <p className="opacity-70">
        No applications shared with this lender yet. Check for applications
        after a borrower shares one.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="table">
        <thead>
          <tr>
            <th>Grant</th>
            <th>Access</th>
            <th>Expires</th>
            <th>Last fetch</th>
            <th>Listed SHA-256</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {grants.map((g) => (
            <GrantRow key={g.grantId} clientId={clientId} grant={g} />
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default GrantsTable;
