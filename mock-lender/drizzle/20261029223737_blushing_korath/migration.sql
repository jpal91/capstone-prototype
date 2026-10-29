CREATE TABLE "core_grant" (
	"client_id" text,
	"grant_id" integer,
	"listed_sha256" text NOT NULL,
	"first_seen_at" timestamp with time zone DEFAULT now() NOT NULL,
	"last_listed_at" timestamp with time zone DEFAULT now() NOT NULL,
	"expires_at" timestamp with time zone NOT NULL,
	"access_ended_at" timestamp with time zone,
	"last_fetch_status" text,
	CONSTRAINT "core_grant_pkey" PRIMARY KEY("client_id","grant_id")
);
--> statement-breakpoint
CREATE TABLE "received_copy" (
	"id" serial PRIMARY KEY,
	"client_id" integer NOT NULL,
	"grant_id" integer NOT NULL,
	"sha256" text NOT NULL,
	"xml" bytea NOT NULL,
	"fetched_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "received_copy_client_id_grant_id_unique" UNIQUE("client_id","grant_id")
);
--> statement-breakpoint
ALTER TABLE "received_copy" ADD CONSTRAINT "received_copy_HSZ4QhNDTwZu_fkey" FOREIGN KEY ("client_id","grant_id") REFERENCES "core_grant"("client_id","grant_id");