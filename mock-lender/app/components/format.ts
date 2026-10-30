// Rendered on the server, so times are in the server's time zone (UTC in the
// container); the zone name is shown so that's never ambiguous.
// (dateStyle/timeStyle can't be combined with timeZoneName.)
const dateTime = new Intl.DateTimeFormat("en-US", {
  year: "numeric",
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
  timeZoneName: "short",
});

export const formatDateTime = (iso: string) => dateTime.format(new Date(iso));
