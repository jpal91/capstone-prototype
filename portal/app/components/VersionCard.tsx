import type { components } from "@/app/lib/core/schema";
import { formatDateTime } from "./format";

type Version = components["schemas"]["VersionItemResponse"];
type Grant = components["schemas"]["GrantResponse"];

type VersionCardProps = {
  version: Version;
  isLatest: boolean;
  // Differs from the latest version (an unchanged draft finalizes to the same bytes).
  isOutdated: boolean;
  // null when the grants couldn't be loaded.
  grants: Grant[] | null;
};

const STATUS_BADGE: Record<Grant["status"], string> = {
  active: "badge-success",
  expired: "badge-neutral",
  revoked: "badge-error",
};

const GrantRow = ({ grant }: { grant: Grant }) => (
  <li className="flex flex-col gap-1 py-2">
    <div className="flex items-center justify-between gap-2">
      <span className="font-medium">{grant.lenderName}</span>
      <span className={`badge badge-sm ${STATUS_BADGE[grant.status]}`}>
        {grant.status}
      </span>
    </div>
    <div className="text-xs opacity-70">
      {grant.status === "active" && (
        <>Expires {formatDateTime(grant.expiresAt)} · </>
      )}
      {grant.status === "revoked" && grant.revokedAt && (
        <>Revoked {formatDateTime(grant.revokedAt)} · </>
      )}
      {grant.lastFetchedAt
        ? `Last fetched ${formatDateTime(grant.lastFetchedAt)}`
        : "Not fetched yet"}
    </div>
  </li>
);

const VersionCard = ({
  version,
  isLatest,
  isOutdated,
  grants,
}: VersionCardProps) => {
  // Active grants first; otherwise in the order they were created.
  const sorted = grants?.toSorted(
    (a, b) => Number(b.status === "active") - Number(a.status === "active"),
  );
  const hasActive = grants?.some((g) => g.status === "active") ?? false;
  // The exact bytes lenders receive (MISMO XML).
  const xmlHref = `/borrower/versions/${version.id}/xml`;

  return (
    <div className="card card-border bg-base-100">
      <div className="card-body">
        <div className="flex items-center justify-between">
          <h3 className="card-title">Version {version.number}</h3>
          {isLatest && <span className="badge badge-primary">Latest</span>}
        </div>

        <div className="text-sm">
          <div>Finalized {formatDateTime(version.createdAt)}</div>
          <div title={version.sha256}>
            SHA-256{" "}
            <span className="font-mono">{version.sha256.slice(0, 12)}…</span>
          </div>
        </div>

        {isOutdated && hasActive && (
          <div role="alert" className="alert alert-warning text-sm">
            Lenders with access to this version don&apos;t see changes in newer
            versions.
          </div>
        )}

        <div>
          <h4 className="text-sm font-semibold">Shared with</h4>
          {sorted === undefined ? (
            <p className="text-sm text-error">
              Sharing status couldn&apos;t be loaded.
            </p>
          ) : sorted.length === 0 ? (
            <p className="text-sm opacity-70">Not shared with any lender.</p>
          ) : (
            <ul className="divide-y divide-base-300">
              {sorted.map((g) => (
                <GrantRow key={g.id} grant={g} />
              ))}
            </ul>
          )}
        </div>

        {/* Plain <a>: these go to a route handler, not a page. */}
        <div className="card-actions justify-end">
          <a
            href={xmlHref}
            target="_blank"
            rel="noopener"
            className="btn btn-ghost btn-sm"
          >
            View XML
          </a>
          <a
            href={xmlHref}
            download={`pre-application-v${version.number}.xml`}
            className="btn btn-sm"
          >
            Download
          </a>
        </div>
      </div>
    </div>
  );
};

export default VersionCard;
