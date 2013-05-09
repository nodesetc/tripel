\set SCHEMA_NAME 'tripel'

CREATE SCHEMA :SCHEMA_NAME;

CREATE TYPE :SCHEMA_NAME.metaspace_privilege_t AS ENUM ('create_user', 'create_space', 'super');
CREATE TYPE :SCHEMA_NAME.nodespace_privilege_t AS ENUM ('contributor', 'editor', 'moderator', 'admin');
CREATE TYPE :SCHEMA_NAME.auth_event_t AS ENUM ('session_created', 'session_killed', 'session_cleaned', 'password_check_success', 'password_check_fail');

CREATE TABLE :SCHEMA_NAME.users (
	user_id SERIAL PRIMARY KEY,
	email_addr VARCHAR(200) NOT NULL UNIQUE, --TODO: sort of want to drop the NOT NULL constraint
	username VARCHAR(100) NOT NULL UNIQUE,
	encrypted_password VARCHAR(200) NOT NULL, --for now, using a bcrypt implementation which obviates the need for separate salt and encryption method fields
	user_statement VARCHAR(1000),
	is_enabled BOOLEAN NOT NULL,
	metaspace_privileges :SCHEMA_NAME.metaspace_privilege_t[],
	creator INTEGER REFERENCES :SCHEMA_NAME.users(user_id),
	creation_date TIMESTAMP WITH TIME ZONE NOT NULL,
	modifier INTEGER REFERENCES :SCHEMA_NAME.users(user_id),
	modification_date TIMESTAMP WITH TIME ZONE
);

--TODO: when writing the session stuff, block further access until user logging in resets pw after another user resets it
CREATE TABLE :SCHEMA_NAME.password_change_audit_log (
	passwd_chg_id SERIAL PRIMARY KEY,
	updated_user INTEGER REFERENCES :SCHEMA_NAME.users(user_id) NOT NULL,
	updating_user INTEGER REFERENCES :SCHEMA_NAME.users(user_id) NOT NULL,
	passwd_chg_date TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE :SCHEMA_NAME.metaspace_privilege_audit_log (
	ms_priv_chg_id SERIAL PRIMARY KEY,
	updated_user INTEGER REFERENCES :SCHEMA_NAME.users(user_id) NOT NULL,
	updating_user INTEGER REFERENCES :SCHEMA_NAME.users(user_id),
	is_enabled BOOLEAN NOT NULL,
	new_privileges :SCHEMA_NAME.metaspace_privilege_t[],
	ms_priv_chg_date TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE :SCHEMA_NAME.auth_event_log (
	auth_event_id SERIAL PRIMARY KEY,
	user_id INTEGER REFERENCES :SCHEMA_NAME.users(user_id) NOT NULL,
	auth_event :SCHEMA_NAME.auth_event_t NOT NULL,
	auth_event_date TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE :SCHEMA_NAME.metaspace_invitations (
	metaspace_invitation_id SERIAL PRIMARY KEY,
	metaspace_invitation_code VARCHAR(100) NOT NULL UNIQUE,
	invitee_email_addr VARCHAR(200) NOT NULL,
	initial_metaspace_privileges :SCHEMA_NAME.metaspace_privilege_t[],
	invitation_msg VARCHAR(1000),
	creator INTEGER REFERENCES :SCHEMA_NAME.users(user_id) NOT NULL,
	creation_date TIMESTAMP WITH TIME ZONE NOT NULL,
	decision_date TIMESTAMP WITH TIME ZONE,
	was_accepted BOOLEAN,
	new_user_id INTEGER REFERENCES :SCHEMA_NAME.users(user_id)
);

CREATE TABLE :SCHEMA_NAME.metaspace_settings (
	metaspace_setting_id INTEGER NOT NULL UNIQUE CHECK (metaspace_setting_id = 0), --stupid hack to make sure there's only one setting row for now
	datamodel_version INTEGER,
	modifier INTEGER REFERENCES :SCHEMA_NAME.users(user_id),
	modification_date TIMESTAMP WITH TIME ZONE
);

CREATE TABLE :SCHEMA_NAME.nodespaces (
	nodespace_id SERIAL PRIMARY KEY,
	nodespace_name VARCHAR(200) NOT NULL UNIQUE,
	nodespace_description VARCHAR(2000),
	default_nodespace_privileges :SCHEMA_NAME.nodespace_privilege_t[],
	creator INTEGER REFERENCES :SCHEMA_NAME.users(user_id) NOT NULL,
	creation_date TIMESTAMP WITH TIME ZONE NOT NULL,
	modifier INTEGER REFERENCES :SCHEMA_NAME.users(user_id),
	modification_date TIMESTAMP WITH TIME ZONE
);

CREATE TABLE :SCHEMA_NAME.nodespace_invitations (
	nodespace_invitation_id SERIAL PRIMARY KEY,
	nodespace_invitation_code VARCHAR(100) NOT NULL UNIQUE,
	invitee_email_addr VARCHAR(200) NOT NULL,
	nodespace_id INTEGER REFERENCES :SCHEMA_NAME.nodespaces(nodespace_id) NOT NULL,
	initial_nodespace_privileges :SCHEMA_NAME.nodespace_privilege_t[],
	invitation_msg VARCHAR(1000),
	creator INTEGER REFERENCES :SCHEMA_NAME.users(user_id) NOT NULL,
	creation_date TIMESTAMP WITH TIME ZONE NOT NULL,
	decision_date TIMESTAMP WITH TIME ZONE,
	was_accepted BOOLEAN,
	user_id INTEGER REFERENCES :SCHEMA_NAME.users(user_id)
);

CREATE TABLE :SCHEMA_NAME.nodespace_access_map (
	nodespace_access_id SERIAL PRIMARY KEY,
	user_id INTEGER REFERENCES :SCHEMA_NAME.users(user_id) NOT NULL,
	nodespace_id INTEGER REFERENCES :SCHEMA_NAME.nodespaces(nodespace_id) NOT NULL,
	is_enabled BOOLEAN NOT NULL,
	nodespace_privileges :SCHEMA_NAME.nodespace_privilege_t[] NOT NULL,
	invitation_id INTEGER REFERENCES :SCHEMA_NAME.nodespace_invitations(nodespace_invitation_id),
	creator INTEGER REFERENCES :SCHEMA_NAME.users(user_id) NOT NULL,
	creation_date TIMESTAMP WITH TIME ZONE NOT NULL,
	modifier INTEGER REFERENCES :SCHEMA_NAME.users(user_id),
	modification_date TIMESTAMP WITH TIME ZONE,
	UNIQUE (nodespace_id, user_id)
);

CREATE TABLE :SCHEMA_NAME.metaspace_sessions (
	metaspace_session_id VARCHAR(100) PRIMARY KEY,
	user_id INTEGER NOT NULL UNIQUE REFERENCES :SCHEMA_NAME.users(user_id),
	creation_date TIMESTAMP WITH TIME ZONE NOT NULL,
	last_visit TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE SEQUENCE :SCHEMA_NAME.unique_neo_node_id;
CREATE SEQUENCE :SCHEMA_NAME.unique_neo_edge_id;
