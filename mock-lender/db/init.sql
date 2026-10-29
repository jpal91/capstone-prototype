CREATE ROLE lender LOGIN PASSWORD 'lender';
CREATE DATABASE lender OWNER lender;
-- Each role can connect only to its own database. (core is a superuser
-- and bypasses this; that's L-06.)
REVOKE CONNECT ON DATABASE lender FROM PUBLIC;
REVOKE CONNECT ON DATABASE core FROM PUBLIC;
