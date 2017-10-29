-- =============================================================================
-- Diagram Name: pynhldb - Database Design
-- Created on: 29.10.2017 02:10:32
-- Diagram Version: 1.4
-- =============================================================================
CREATE SCHEMA "nhl";



SET CHECK_FUNCTION_BODIES TO FALSE;

CREATE OR REPLACE FUNCTION "nhl"."tr_log_actions" () 	
RETURNS trigger AS
$BODY$
declare
v_old_data text;
v_new_data text;
begin
if (tg_op = 'UPDATE') then
v_old_data := row(old.*);
v_new_data := row(new.*);
insert into nhl.logged_actions (schema_name, table_name, user_name, action, original_data, new_data, query)
values (tg_table_schema::text, tg_table_name::text, session_user::text, substring(tg_op,1,1), v_old_data, v_new_data, current_query());
return new;
elsif (tg_op = 'DELETE') then
v_old_data := row(old.*);
insert into nhl.logged_actions (schema_name, table_name, user_name, action, original_data, query)
values (tg_table_schema::text, tg_table_name::text, session_user::text, substring(tg_op,1,1), v_old_data, current_query());
return old;
elsif (tg_op = 'INSERT') then
v_new_data := row(new.*);
insert into nhl.logged_actions (schema_name, table_name, user_name, action, new_data, query)
values (tg_table_schema::text, tg_table_name::text, session_user::text, substring(tg_op,1,1), v_new_data, current_query());
return new;
else
raise warning '[TR_LOG_ACTIONS] - Other action occurred: %, at %', tg_op, now();
return null;
end if;
exception
when data_exception then
raise warning '[TR_LOG_ACTIONS] - UDF ERROR [DATA EXCEPTION] - SQLSTATE: %, SQLERRM: %', SQLSTATE, SQLERRM;
return null;
when unique_violation then
raise warning '[TR_LOG_ACTIONS] - UDF ERROR [UNIQUE] - SQLSTATE: %, SQLERRM: %', SQLSTATE, SQLERRM;
return null;
when others then
raise warning '[TR_LOG_ACTIONS] - UDF ERROR [OTHER] - SQLSTATE: %, SQLERRM: %', SQLSTATE, SQLERRM;
return null;
end;
$BODY$
	LANGUAGE PLpgSQL
	CALLED ON NULL INPUT
	VOLATILE
	EXTERNAL SECURITY DEFINER
	COST 100;




CREATE OR REPLACE FUNCTION "nhl"."tr_partition_logged_actions" () 	
RETURNS trigger AS
$BODY$
DECLARE
_tablename text;
_startdate text;
_enddate text;
_currmonth text;
BEGIN
_currmonth := to_char(NEW.action_tstamp, 'YYYY_MM');
_tablename := 'logged_actions_'||_currmonth;
_startdate := date_trunc('month', NEW.action_tstamp);

-- Check if the partition needed for the current record exists
PERFORM 1
FROM   pg_catalog.pg_class c
JOIN   pg_catalog.pg_namespace n ON n.oid = c.relnamespace
WHERE  c.relkind = 'r'
AND    c.relname = _tablename
AND    n.nspname = tg_table_schema::text;

-- If the partition needed does not yet exist, then we create it:
-- Note that || is string concatenation (joining two strings to make one)
IF NOT FOUND THEN
_enddate := date_trunc('month', NEW.action_tstamp) + interval '1 month';
EXECUTE 'CREATE TABLE ' || tg_table_schema::text || '.' || quote_ident(_tablename) || ' (
CHECK ( action_tstamp >= ' || quote_literal(_startdate) || '
AND action_tstamp < ' || quote_literal(_enddate) || ')
) INHERITS (' || tg_table_schema::text || '.logged_actions)';

-- Table permissions are not inherited from the parent.
-- If permissions change on the master be sure to change them on the child also.
EXECUTE 'ALTER TABLE ' || tg_table_schema::text || '.' || quote_ident(_tablename) || ' OWNER TO nhl_user';
EXECUTE 'GRANT ALL ON TABLE ' || tg_table_schema::text || '.' || quote_ident(_tablename) || ' TO nhl_user';

-- Indexes are defined per child, so we assign a default index that uses the partition columns
EXECUTE 'CREATE INDEX ' || quote_ident(_tablename||'_indx1') || ' ON ' || tg_table_schema::text || '.' || quote_ident(_tablename) || ' (action_tstamp, action)';
END IF;

-- Insert the current record into the correct partition, which we are sure will now exist.
EXECUTE 'INSERT INTO ' || tg_table_schema::text || '.' || quote_ident(_tablename) || ' VALUES ($1.*)' USING NEW;
RETURN NULL;
END;
$BODY$
	LANGUAGE PLpgSQL
	CALLED ON NULL INPUT
	VOLATILE
	EXTERNAL SECURITY DEFINER;




SET CHECK_FUNCTION_BODIES TO TRUE;


DROP TABLE IF EXISTS "nhl"."teams" CASCADE;

CREATE TABLE "nhl"."teams" (
	"team_id" int4 NOT NULL,
	"franchise_id" int4 NOT NULL,
	"name" varchar NOT NULL,
	"short_name" varchar,
	"team_name" varchar NOT NULL,
	"abbr" char(3) NOT NULL,
	"orig_abbr" char(3) NOT NULL,
	"first_year_of_play" int4 NOT NULL,
	"last_year_of_play" int4 DEFAULT NULL,
	CONSTRAINT "team_key" PRIMARY KEY("team_id")
);

ALTER TABLE "nhl"."teams" OWNER TO "nhl_user";

COMMENT ON TABLE "nhl"."teams" IS 'National Hockey League teams';

COMMENT ON COLUMN "nhl"."teams"."team_id" IS 'Unique team ID as used by NHL stats API';

COMMENT ON COLUMN "nhl"."teams"."franchise_id" IS 'Unique franchise ID as used by NHL stats API';

COMMENT ON COLUMN "nhl"."teams"."name" IS 'Full team name';

COMMENT ON COLUMN "nhl"."teams"."short_name" IS 'Short team name, usually geography related';

COMMENT ON COLUMN "nhl"."teams"."team_name" IS 'Team nick name';

COMMENT ON COLUMN "nhl"."teams"."abbr" IS 'Team abbreviation as used by NHL stats API';

COMMENT ON COLUMN "nhl"."teams"."orig_abbr" IS 'Team abbreviation as used in play-by-play-data, game summaries and event reports';

COMMENT ON COLUMN "nhl"."teams"."first_year_of_play" IS 'Actual first year of play for this team in the National Hockey League, doesn''t necessarily correspond with parameter firstYearOfPlay in JSON structure at https://statsapi.web.nhl.com/api/v1/teams/';

COMMENT ON COLUMN "nhl"."teams"."last_year_of_play" IS 'Actual last year of play of this team in the National Hockey League';

DROP TABLE IF EXISTS "nhl"."divisions" CASCADE;

CREATE TABLE "nhl"."divisions" (
	"division_id" SERIAL NOT NULL,
	"division_name" varchar,
	"season" int4,
	"teams" int4[],
	"conference" varchar,
	CONSTRAINT "division_key" PRIMARY KEY("division_id")
);

ALTER TABLE "nhl"."divisions" OWNER TO "nhl_user";

COMMENT ON TABLE "nhl"."divisions" IS 'National Hockey League divisions';

COMMENT ON COLUMN "nhl"."divisions"."division_id" IS 'Unique division ID as auto-incremental number';

COMMENT ON COLUMN "nhl"."divisions"."division_name" IS 'Name of the division';

COMMENT ON COLUMN "nhl"."divisions"."season" IS 'Year in which the current division existed';

COMMENT ON COLUMN "nhl"."divisions"."teams" IS 'List of team ids in the current division';

COMMENT ON COLUMN "nhl"."divisions"."conference" IS 'Name of the conference (optionally)';

DROP TABLE IF EXISTS "nhl"."players" CASCADE;















CREATE TABLE "nhl"."players" (
	"player_id" int4 NOT NULL,
	"last_name" varchar NOT NULL,
	"first_name" varchar NOT NULL,
	"position" char(1),
	"alternate_last_names" varchar[],
	"alternate_first_names" varchar[],
	"alternate_positions" char[],
	"capfriendly_id" varchar,
	CONSTRAINT "player_key" PRIMARY KEY("player_id"),
	CONSTRAINT "position_check" CHECK(position in ('G', 'D', 'L', 'C', 'R', 'F', 'W', '')),
	CONSTRAINT "alternate_position_check" CHECK(alternate_positions <@ ARRAY['G', 'D', 'L', 'C', 'R', 'F', 'W', '', NULL]::char[])
);

CREATE TRIGGER "players_audit" AFTER INSERT OR UPDATE OR DELETE
	ON "nhl"."players" FOR EACH ROW
	EXECUTE PROCEDURE "nhl"."tr_log_actions"();


ALTER TABLE "nhl"."players" OWNER TO "nhl_user";

COMMENT ON TABLE "nhl"."players" IS 'National Hockey League players';

COMMENT ON COLUMN "nhl"."players"."player_id" IS 'Player ID as used by NHL stats api';

COMMENT ON COLUMN "nhl"."players"."last_name" IS 'Last name of the player';

COMMENT ON COLUMN "nhl"."players"."first_name" IS 'First name of the player';

COMMENT ON COLUMN "nhl"."players"."position" IS 'Position of the player';

COMMENT ON COLUMN "nhl"."players"."alternate_last_names" IS 'Alternate last names of the player';

COMMENT ON COLUMN "nhl"."players"."alternate_first_names" IS 'Alternate first names of the player';

COMMENT ON COLUMN "nhl"."players"."alternate_positions" IS 'Alternate positions of the player';

COMMENT ON COLUMN "nhl"."players"."capfriendly_id" IS 'Player id as used by capfriendly.com';

DROP TABLE IF EXISTS "nhl"."logged_actions" CASCADE;

CREATE TABLE "nhl"."logged_actions" (
	"action_id" SERIAL NOT NULL,
	"schema_name" text NOT NULL,
	"table_name" text NOT NULL,
	"user_name" text,
	"action_tstamp" timestamp with time zone NOT NULL DEFAULT now(),
	"action" text NOT NULL,
	"original_data" text,
	"new_data" text,
	"query" text,
	CONSTRAINT "logged_actions_action_check" CHECK(action = ANY (ARRAY['I'::text, 'D'::text, 'U'::text]))
)
WITH (
	FILLFACTOR = 100,
	OIDS = False
);

CREATE INDEX "logged_actions_schema_table_idx" ON "nhl"."logged_actions" USING BTREE (
	((schema_name || '.'::text) || table_name)
);


CREATE INDEX "logged_actions_action_tstamp_idx" ON "nhl"."logged_actions" USING BTREE (
	"action_tstamp"
);


CREATE INDEX "logged_actions_action_idx" ON "nhl"."logged_actions" USING BTREE (
	"action"
);


CREATE TRIGGER "logged_actions_trigger" BEFORE INSERT 
	ON "nhl"."logged_actions" FOR EACH ROW
	EXECUTE PROCEDURE "nhl"."tr_partition_logged_actions"();


ALTER TABLE "nhl"."logged_actions" OWNER TO "nhl_user";

GRANT SELECT ON TABLE "nhl"."logged_actions" TO PUBLIC;

COMMENT ON TABLE "nhl"."logged_actions" IS 'Logged insert, update and delete actions for selected tables in the current schema';

DROP TABLE IF EXISTS "nhl"."player_seasons" CASCADE;

CREATE TABLE "nhl"."player_seasons" (
	"player_season_id" SERIAL NOT NULL,
	"player_id" int4,
	"season" int2,
	"team_id" int4,
	"season_team_sequence" int2,
	"season_type" varchar(2),
	"games_played" int2,
	"goals" int2,
	"assists" int2,
	"points" int2,
	"plus_minus" int2,
	"pim" int2,
	"ppg" int2,
	"pp_pts" int4,
	"shg" int2,
	"sh_pts" int4,
	"gwg" int2,
	"otg" int4,
	"shots" int2,
	"pctg" numeric,
	"hits" int4,
	"blocks" int4,
	"shifts" int4,
	"toi" interval(0),
	"ev_toi" interval(0),
	"pp_toi" interval(0),
	"sh_toi" interval(0),
	"faceoff_pctg" numeric,
	CONSTRAINT "player_season_key" PRIMARY KEY("player_season_id")
);

CREATE TRIGGER "player_seasons_audit" AFTER INSERT OR UPDATE OR DELETE
	ON "nhl"."player_seasons" FOR EACH ROW
	EXECUTE PROCEDURE "nhl"."tr_log_actions"();


ALTER TABLE "nhl"."player_seasons" OWNER TO "nhl_user";

COMMENT ON TABLE "nhl"."player_seasons" IS 'Skater season statistics in the National Hockey League';

COMMENT ON COLUMN "nhl"."player_seasons"."player_season_id" IS 'Unique player season ID as auto-incremental number';

COMMENT ON COLUMN "nhl"."player_seasons"."player_id" IS 'Related player ID';

COMMENT ON COLUMN "nhl"."player_seasons"."season" IS 'Related season';

COMMENT ON COLUMN "nhl"."player_seasons"."team_id" IS 'Related team ID';

COMMENT ON COLUMN "nhl"."player_seasons"."season_team_sequence" IS 'Team sequence number, e.g. in case of multiple teams per season';

COMMENT ON COLUMN "nhl"."player_seasons"."season_type" IS 'Season type, e.g. regular season or playoffs';

COMMENT ON COLUMN "nhl"."player_seasons"."games_played" IS 'Games played';

COMMENT ON COLUMN "nhl"."player_seasons"."goals" IS 'Goals';

COMMENT ON COLUMN "nhl"."player_seasons"."assists" IS 'Assists';

COMMENT ON COLUMN "nhl"."player_seasons"."points" IS 'Points';

COMMENT ON COLUMN "nhl"."player_seasons"."plus_minus" IS 'Plus-minus rating';

COMMENT ON COLUMN "nhl"."player_seasons"."pim" IS 'Penalty minutes';

COMMENT ON COLUMN "nhl"."player_seasons"."ppg" IS 'Power-play goals';

COMMENT ON COLUMN "nhl"."player_seasons"."pp_pts" IS 'Power-play points';

COMMENT ON COLUMN "nhl"."player_seasons"."shg" IS 'Shorthanded goals';

COMMENT ON COLUMN "nhl"."player_seasons"."sh_pts" IS 'Shorthanded points';

COMMENT ON COLUMN "nhl"."player_seasons"."gwg" IS 'Game-winning goals';

COMMENT ON COLUMN "nhl"."player_seasons"."otg" IS 'Overtime goals';

COMMENT ON COLUMN "nhl"."player_seasons"."shots" IS 'Shots on goal';

COMMENT ON COLUMN "nhl"."player_seasons"."pctg" IS 'Shooting percentage';

COMMENT ON COLUMN "nhl"."player_seasons"."hits" IS 'Hits';

COMMENT ON COLUMN "nhl"."player_seasons"."blocks" IS 'Blocked shots';

COMMENT ON COLUMN "nhl"."player_seasons"."shifts" IS 'Number of shifts';

COMMENT ON COLUMN "nhl"."player_seasons"."toi" IS 'Overall time on ice';

COMMENT ON COLUMN "nhl"."player_seasons"."ev_toi" IS 'Even-strength time on ice';

COMMENT ON COLUMN "nhl"."player_seasons"."pp_toi" IS 'Powerplay time on ice';

COMMENT ON COLUMN "nhl"."player_seasons"."sh_toi" IS 'Shorthanded time on ice';

COMMENT ON COLUMN "nhl"."player_seasons"."faceoff_pctg" IS 'Faceoff winning percentage';

DROP TABLE IF EXISTS "nhl"."goalie_seasons" CASCADE;

CREATE TABLE "nhl"."goalie_seasons" (
	"goalie_season_id" SERIAL NOT NULL,
	"player_id" int4,
	"season" int2,
	"team_id" int4,
	"season_team_sequence" int2,
	"season_type" varchar(2),
	"games_played" int2,
	"games_started" int2,
	"wins" int2,
	"losses" int2,
	"ties" int2,
	"otl" int2,
	"ga" int4,
	"sa" int4,
	"saves" int4,
	"save_pctg" numeric,
	"even_sa" int4,
	"even_saves" int4,
	"pp_sa" int4,
	"pp_saves" int4,
	"sh_sa" int4,
	"sh_saves" int4,
	"minutes" int4,
	"toi" interval(0),
	"gaa" numeric,
	"so" int2,
	CONSTRAINT "goalie_season_key" PRIMARY KEY("goalie_season_id")
);

CREATE TRIGGER "goalie_seasons_audit" AFTER INSERT OR UPDATE OR DELETE
	ON "nhl"."goalie_seasons" FOR EACH ROW
	EXECUTE PROCEDURE "nhl"."tr_log_actions"();


COMMENT ON TABLE "nhl"."goalie_seasons" IS 'Goaltender season statistics in the National Hockey League';

COMMENT ON COLUMN "nhl"."goalie_seasons"."goalie_season_id" IS 'Unique goalie season ID as auto-incremental number';

COMMENT ON COLUMN "nhl"."goalie_seasons"."player_id" IS 'Related player ID';

COMMENT ON COLUMN "nhl"."goalie_seasons"."season" IS 'Related season';

COMMENT ON COLUMN "nhl"."goalie_seasons"."team_id" IS 'Related team ID';

COMMENT ON COLUMN "nhl"."goalie_seasons"."season_team_sequence" IS 'Team sequence number, e.g. in case of multiple teams per season';

COMMENT ON COLUMN "nhl"."goalie_seasons"."season_type" IS 'Season type, e.g. regular season or playoffs';

COMMENT ON COLUMN "nhl"."goalie_seasons"."games_played" IS 'Games played';

COMMENT ON COLUMN "nhl"."goalie_seasons"."games_started" IS 'Games started';

COMMENT ON COLUMN "nhl"."goalie_seasons"."wins" IS 'Wins';

COMMENT ON COLUMN "nhl"."goalie_seasons"."losses" IS 'Losses';

COMMENT ON COLUMN "nhl"."goalie_seasons"."ties" IS 'Ties';

COMMENT ON COLUMN "nhl"."goalie_seasons"."otl" IS 'Overtime losses';

COMMENT ON COLUMN "nhl"."goalie_seasons"."ga" IS 'Goals against';

COMMENT ON COLUMN "nhl"."goalie_seasons"."sa" IS 'Shots against';

COMMENT ON COLUMN "nhl"."goalie_seasons"."saves" IS 'Saves';

COMMENT ON COLUMN "nhl"."goalie_seasons"."save_pctg" IS 'Save percentage';

COMMENT ON COLUMN "nhl"."goalie_seasons"."even_sa" IS 'Even strength shots against';

COMMENT ON COLUMN "nhl"."goalie_seasons"."even_saves" IS 'Even strength saves';

COMMENT ON COLUMN "nhl"."goalie_seasons"."pp_sa" IS 'Power-play shots against';

COMMENT ON COLUMN "nhl"."goalie_seasons"."pp_saves" IS 'Power-play saves';

COMMENT ON COLUMN "nhl"."goalie_seasons"."sh_sa" IS 'Shorthanded shots against';

COMMENT ON COLUMN "nhl"."goalie_seasons"."sh_saves" IS 'Shorthanded saves';

COMMENT ON COLUMN "nhl"."goalie_seasons"."minutes" IS 'Minutes played';

COMMENT ON COLUMN "nhl"."goalie_seasons"."toi" IS 'Time on ice';

COMMENT ON COLUMN "nhl"."goalie_seasons"."gaa" IS 'Goals-against average';

COMMENT ON COLUMN "nhl"."goalie_seasons"."so" IS 'Shutouts';

DROP TABLE IF EXISTS "nhl"."player_data" CASCADE;

CREATE TABLE "nhl"."player_data" (
	"player_data_id" SERIAL NOT NULL,
	"player_id" int4,
	"height_metric" numeric(3,2),
	"height_imperial" numeric(3,2),
	"weight_metric" int2,
	"weight_imperial" int2,
	"hand" char(1),
	"date_of_birth" date,
	"place_of_birth" int4,
	"country" varchar,
	"image" bytea,
	"location" varchar(150),
	CONSTRAINT "player_data_key" PRIMARY KEY("player_data_id")
);

CREATE TRIGGER "player_data_audit" AFTER INSERT OR UPDATE OR DELETE
	ON "nhl"."player_data" FOR EACH ROW
	EXECUTE PROCEDURE "nhl"."tr_log_actions"();


ALTER TABLE "nhl"."player_data" OWNER TO "nhl_user";

COMMENT ON TABLE "nhl"."player_data" IS 'Individual information for National Hockey League players';

COMMENT ON COLUMN "nhl"."player_data"."player_data_id" IS 'Unique player data item ID as auto-incremental number';

COMMENT ON COLUMN "nhl"."player_data"."player_id" IS 'Related player ID';

COMMENT ON COLUMN "nhl"."player_data"."height_metric" IS 'Metric height of the player';

COMMENT ON COLUMN "nhl"."player_data"."height_imperial" IS 'Imperial height of the player';

COMMENT ON COLUMN "nhl"."player_data"."weight_metric" IS 'Metric weight of the player';

COMMENT ON COLUMN "nhl"."player_data"."weight_imperial" IS 'Imperial weight of the player';

COMMENT ON COLUMN "nhl"."player_data"."hand" IS 'Handedness of the player';

COMMENT ON COLUMN "nhl"."player_data"."date_of_birth" IS 'Player''s date of birth';

COMMENT ON COLUMN "nhl"."player_data"."place_of_birth" IS 'ID of player''s place of birth';

COMMENT ON COLUMN "nhl"."player_data"."country" IS 'Player''s country of birth';

COMMENT ON COLUMN "nhl"."player_data"."image" IS 'Image of the player';

COMMENT ON COLUMN "nhl"."player_data"."location" IS 'Player''s place of birth actual location';

DROP TABLE IF EXISTS "nhl"."contracts" CASCADE;

CREATE TABLE "nhl"."contracts" (
	"contract_id" uuid NOT NULL,
	"player_id" int4,
	"signing_team_id" int4,
	"signing_date" date,
	"length" int4,
	"value" int4,
	"type" varchar,
	"expiry_status" varchar,
	"source" varchar,
	"start_season" int4,
	"end_season" int4,
	"bought_out" bool,
	"cap_hit_percentage" numeric(4,2),
	"notes" varchar,
	CONSTRAINT "contract_key" PRIMARY KEY("contract_id")
);

CREATE TRIGGER "contracts_audit" AFTER INSERT OR UPDATE OR DELETE
	ON "nhl"."contracts" FOR EACH ROW
	EXECUTE PROCEDURE "nhl"."tr_log_actions"();


ALTER TABLE "nhl"."contracts" OWNER TO "nhl_user";

COMMENT ON TABLE "nhl"."contracts" IS 'National Hockey League contracts';

COMMENT ON COLUMN "nhl"."contracts"."contract_id" IS 'Unique contract ID as auto-incremental number';

COMMENT ON COLUMN "nhl"."contracts"."player_id" IS 'ID of the contracted player';

COMMENT ON COLUMN "nhl"."contracts"."signing_team_id" IS 'ID of the team signing the contract';

COMMENT ON COLUMN "nhl"."contracts"."signing_date" IS 'Date when the contract was signed';

COMMENT ON COLUMN "nhl"."contracts"."length" IS 'Length of the contract in years';

COMMENT ON COLUMN "nhl"."contracts"."value" IS 'Overall value of the contract';

COMMENT ON COLUMN "nhl"."contracts"."type" IS 'Contract type';

COMMENT ON COLUMN "nhl"."contracts"."expiry_status" IS 'Player status after the contract has expired';

COMMENT ON COLUMN "nhl"."contracts"."source" IS 'Source for contract data';

COMMENT ON COLUMN "nhl"."contracts"."start_season" IS 'First season of the contract';

COMMENT ON COLUMN "nhl"."contracts"."end_season" IS 'Last season of the contract';

COMMENT ON COLUMN "nhl"."contracts"."bought_out" IS 'Flag indicating whether the contract was bought out';

COMMENT ON COLUMN "nhl"."contracts"."cap_hit_percentage" IS 'Cap hit percentage of the cap ceiling when the contract was signed';

COMMENT ON COLUMN "nhl"."contracts"."notes" IS 'Additional notes on contract';

DROP TABLE IF EXISTS "nhl"."contract_years" CASCADE;

CREATE TABLE "nhl"."contract_years" (
	"contract_year_id" uuid NOT NULL,
	"contract_id" uuid,
	"player_id" int4,
	"season" int2,
	"cap_hit" int4,
	"aav" int4,
	"nhl_salary" int4,
	"sign_bonus" int4,
	"perf_bonus" int4,
	"minors_salary" int4,
	"clause" varchar,
	"note" varchar,
	"bought_out" bool,
	CONSTRAINT "contract_year_key" PRIMARY KEY("contract_year_id")
);

CREATE TRIGGER "contract_years_audit" AFTER INSERT OR UPDATE OR DELETE
	ON "nhl"."contract_years" FOR EACH ROW
	EXECUTE PROCEDURE "nhl"."tr_log_actions"();


ALTER TABLE "nhl"."contract_years" OWNER TO "nhl_user";

COMMENT ON TABLE "nhl"."contract_years" IS 'National Hockey League contract years';

COMMENT ON COLUMN "nhl"."contract_years"."contract_year_id" IS 'Unique contract year ID as auto-incremental number';

COMMENT ON COLUMN "nhl"."contract_years"."contract_id" IS 'ID of the contract';

COMMENT ON COLUMN "nhl"."contract_years"."player_id" IS 'ID of the player contracted';

COMMENT ON COLUMN "nhl"."contract_years"."season" IS 'Season of the contract year';

COMMENT ON COLUMN "nhl"."contract_years"."cap_hit" IS 'Annual average salary excluding performance bonuses';

COMMENT ON COLUMN "nhl"."contract_years"."aav" IS 'Annual average salary factoring in performance bonuses';

COMMENT ON COLUMN "nhl"."contract_years"."nhl_salary" IS 'Player salary in the NHL including signing bonuses';

COMMENT ON COLUMN "nhl"."contract_years"."sign_bonus" IS 'Amount of the NHL salary paid as a signing bonus';

COMMENT ON COLUMN "nhl"."contract_years"."perf_bonus" IS 'Maximum performance bonuses for given season';

COMMENT ON COLUMN "nhl"."contract_years"."minors_salary" IS 'Player salary if assigned to a North-American minor-pro league';

COMMENT ON COLUMN "nhl"."contract_years"."clause" IS 'Any kind of clause valid for this contract year';

COMMENT ON COLUMN "nhl"."contract_years"."note" IS 'Additional note on this contract year';

COMMENT ON COLUMN "nhl"."contract_years"."bought_out" IS 'Flag indicating whether this contract year has been bought out';

DROP TABLE IF EXISTS "nhl"."buyouts" CASCADE;

CREATE TABLE "nhl"."buyouts" (
	"buyout_id" uuid NOT NULL,
	"contract_id" uuid,
	"player_id" int4,
	"buyout_team_id" int4,
	"buyout_date" date,
	"length" int4,
	"value" int4,
	"start_season" int4,
	"end_season" int4,
	CONSTRAINT "buyout_key" PRIMARY KEY("buyout_id")
);

CREATE TRIGGER "buyouts_audit" AFTER INSERT OR UPDATE OR DELETE
	ON "nhl"."buyouts" FOR EACH ROW
	EXECUTE PROCEDURE "nhl"."tr_log_actions"();


ALTER TABLE "nhl"."buyouts" OWNER TO "nhl_user";

COMMENT ON TABLE "nhl"."buyouts" IS 'National Hockey League contract buyouts';

COMMENT ON COLUMN "nhl"."buyouts"."buyout_id" IS 'Unique buyout ID as auto-incremental number';

COMMENT ON COLUMN "nhl"."buyouts"."contract_id" IS 'ID of contract bought out';

COMMENT ON COLUMN "nhl"."buyouts"."player_id" IS 'ID of player bought out';

COMMENT ON COLUMN "nhl"."buyouts"."buyout_team_id" IS 'ID of team conducting the contract buyout';

COMMENT ON COLUMN "nhl"."buyouts"."buyout_date" IS 'Date of the contract buyout';

COMMENT ON COLUMN "nhl"."buyouts"."length" IS 'Length of the contract buyout';

COMMENT ON COLUMN "nhl"."buyouts"."value" IS 'Total value of the contract buyout';

COMMENT ON COLUMN "nhl"."buyouts"."start_season" IS 'First year of the contract buyout';

COMMENT ON COLUMN "nhl"."buyouts"."end_season" IS 'Last year of the contract buyout';

DROP TABLE IF EXISTS "nhl"."buyout_years" CASCADE;

CREATE TABLE "nhl"."buyout_years" (
	"buyout_year_id" uuid NOT NULL,
	"buyout_id" uuid,
	"player_id" int4,
	"season" int4,
	"cost" int4,
	"cap_hit" int4,
	CONSTRAINT "buyout_year_key" PRIMARY KEY("buyout_year_id")
);

CREATE TRIGGER "buyout_years_audit" AFTER INSERT OR UPDATE OR DELETE
	ON "nhl"."buyout_years" FOR EACH ROW
	EXECUTE PROCEDURE "nhl"."tr_log_actions"();


ALTER TABLE "nhl"."buyout_years" OWNER TO "nhl_user";

COMMENT ON TABLE "nhl"."buyout_years" IS 'National Hockey League buyout years';

COMMENT ON COLUMN "nhl"."buyout_years"."buyout_year_id" IS 'Unique buyout year ID as auto-incremental number';

COMMENT ON COLUMN "nhl"."buyout_years"."buyout_id" IS 'ID of the corresponding buyout';

COMMENT ON COLUMN "nhl"."buyout_years"."player_id" IS 'ID of player bought out';

COMMENT ON COLUMN "nhl"."buyout_years"."season" IS 'Year of the buyout';

COMMENT ON COLUMN "nhl"."buyout_years"."cost" IS 'Cost of the contract buyout for given year';

COMMENT ON COLUMN "nhl"."buyout_years"."cap_hit" IS 'Cap hit of the contract buyout for the given year';

DROP TABLE IF EXISTS "nhl"."player_drafts" CASCADE;

CREATE TABLE "nhl"."player_drafts" (
	"player_draft_id" SERIAL NOT NULL,
	"player_id" int4,
	"team_id" int4,
	"year" int4,
	"round" int2,
	"overall" int2,
	"draft_type" char(1) DEFAULT 'e',
	CONSTRAINT "player_draft_key" PRIMARY KEY("player_draft_id")
);

CREATE TRIGGER "player_drafts_audit" AFTER INSERT OR UPDATE OR DELETE
	ON "nhl"."player_drafts" FOR EACH ROW
	EXECUTE PROCEDURE "nhl"."tr_log_actions"();


ALTER TABLE "nhl"."player_drafts" OWNER TO "nhl_user";

COMMENT ON TABLE "nhl"."player_drafts" IS 'Individual draft information for National Hockey League players';

COMMENT ON COLUMN "nhl"."player_drafts"."player_draft_id" IS 'Unique player draft item ID as auto-incremental number';

COMMENT ON COLUMN "nhl"."player_drafts"."player_id" IS 'Related player ID';

COMMENT ON COLUMN "nhl"."player_drafts"."team_id" IS 'Team for which the player was drafted';

COMMENT ON COLUMN "nhl"."player_drafts"."year" IS 'Year in which the player was drafted';

COMMENT ON COLUMN "nhl"."player_drafts"."round" IS 'Round in which the player was drafted';

COMMENT ON COLUMN "nhl"."player_drafts"."overall" IS 'Overall draft position';

COMMENT ON COLUMN "nhl"."player_drafts"."draft_type" IS 'Type of the draft';

DROP TABLE IF EXISTS "nhl"."games" CASCADE;

CREATE TABLE "nhl"."games" (
	"game_id" int4 NOT NULL,
	"season" int2,
	"type" int2,
	"date" date,
	"start" timestamp with time zone,
	"end" timestamp with time zone,
	"attendance" int4,
	"venue" varchar,
	"road_team_id" int4,
	"home_team_id" int4,
	"road_score" int2,
	"home_score" int2,
	"road_overall_game_count" int2,
	"home_overall_game_count" int2,
	"road_game_count" int2,
	"home_game_count" int2,
	"data_last_modified" timestamp with time zone,
	"shootout_game" bool,
	"overtime_game" bool,
	"star_1" int4,
	"star_2" int4,
	"star_3" int4,
	"referee_1" varchar,
	"referee_2" varchar,
	"linesman_1" varchar,
	"linesman_2" varchar,
	CONSTRAINT "game_key" PRIMARY KEY("game_id")
);

CREATE TRIGGER "games_audit" AFTER INSERT OR UPDATE OR DELETE
	ON "nhl"."games" FOR EACH ROW
	EXECUTE PROCEDURE "nhl"."tr_log_actions"();


ALTER TABLE "nhl"."games" OWNER TO "nhl_user";

COMMENT ON TABLE "nhl"."games" IS 'National Hockey League games';

COMMENT ON COLUMN "nhl"."games"."game_id" IS 'Unique game ID as combination of season and official game ID';

COMMENT ON COLUMN "nhl"."games"."season" IS 'Season of the game';

COMMENT ON COLUMN "nhl"."games"."type" IS 'Type of the game, e.g. regular season or playoff';

COMMENT ON COLUMN "nhl"."games"."date" IS 'Starting date of the game';

COMMENT ON COLUMN "nhl"."games"."start" IS 'Actual starting time';

COMMENT ON COLUMN "nhl"."games"."end" IS 'Actual ending time';

COMMENT ON COLUMN "nhl"."games"."attendance" IS 'Game attendance';

COMMENT ON COLUMN "nhl"."games"."venue" IS 'Game venue';

COMMENT ON COLUMN "nhl"."games"."road_team_id" IS 'ID of team happening to be the road team';

COMMENT ON COLUMN "nhl"."games"."home_team_id" IS 'ID of team happening to be the home team';

COMMENT ON COLUMN "nhl"."games"."road_score" IS 'Road team score';

COMMENT ON COLUMN "nhl"."games"."home_score" IS 'Home team score';

COMMENT ON COLUMN "nhl"."games"."road_overall_game_count" IS 'Road team overall game count';

COMMENT ON COLUMN "nhl"."games"."home_overall_game_count" IS 'Home team overall game count';

COMMENT ON COLUMN "nhl"."games"."road_game_count" IS 'Road team road game count';

COMMENT ON COLUMN "nhl"."games"."home_game_count" IS 'Home team home game count';

COMMENT ON COLUMN "nhl"."games"."data_last_modified" IS 'Timestamp for last modification';

COMMENT ON COLUMN "nhl"."games"."shootout_game" IS 'Shootout game indicator';

COMMENT ON COLUMN "nhl"."games"."overtime_game" IS 'Overtime game indicator';

COMMENT ON COLUMN "nhl"."games"."star_1" IS 'The game''s 1st star';

COMMENT ON COLUMN "nhl"."games"."star_2" IS 'The game''s 2nd star';

COMMENT ON COLUMN "nhl"."games"."star_3" IS 'The game''s 3rd star';

COMMENT ON COLUMN "nhl"."games"."referee_1" IS 'The game''s one referee';

COMMENT ON COLUMN "nhl"."games"."referee_2" IS 'The game''s other referee';

COMMENT ON COLUMN "nhl"."games"."linesman_1" IS 'The game''s one linesman';

COMMENT ON COLUMN "nhl"."games"."linesman_2" IS 'The game''s other linesman';

DROP TABLE IF EXISTS "nhl"."player_games" CASCADE;

CREATE TABLE "nhl"."player_games" (
	"player_game_id" int8 NOT NULL,
	"game_id" int4,
	"player_id" int4,
	"team_id" int4,
	"position" char(1),
	"no" int2,
	"goals" int2,
	"assists" int2,
	"primary_assists" int2,
	"secondary_assists" int2,
	"points" int2,
	"plus_minus" int2,
	"penalties" int2,
	"pim" int2,
	"toi_overall" interval(0),
	"toi_pp" interval(0),
	"toi_sh" interval(0),
	"toi_ev" interval(0),
	"avg_shift" interval(0),
	"no_shifts" int2,
	"shots_on_goal" int2,
	"shots_blocked" int2,
	"shots_missed" int2,
	"hits" int2,
	"giveaways" int2,
	"takeaways" int2,
	"blocks" int2,
	"faceoffs_won" int2,
	"faceoffs_lost" int2,
	"on_ice_shots_on_goal" int2,
	"on_ice_shots_blocked" int2,
	"on_ice_shots_missed" int2,
	CONSTRAINT "player_game_key" PRIMARY KEY("player_game_id"),
	CONSTRAINT "position_check" CHECK(position in ('G', 'D', 'L', 'C', 'R', 'F', 'W', ''))
);

CREATE TRIGGER "player_games_audit" AFTER INSERT OR UPDATE OR DELETE
	ON "nhl"."player_games" FOR EACH ROW
	EXECUTE PROCEDURE "nhl"."tr_log_actions"();


ALTER TABLE "nhl"."player_games" OWNER TO "nhl_user";

COMMENT ON TABLE "nhl"."player_games" IS 'National Hockey League players in games';

COMMENT ON COLUMN "nhl"."player_games"."player_game_id" IS 'Unique player game ID as combination of game ID, player ID and team ID';

COMMENT ON COLUMN "nhl"."player_games"."game_id" IS 'Related game ID';

COMMENT ON COLUMN "nhl"."player_games"."player_id" IS 'Related player ID';

COMMENT ON COLUMN "nhl"."player_games"."team_id" IS 'Related team ID';

COMMENT ON COLUMN "nhl"."player_games"."position" IS 'Player''s position in game';

COMMENT ON COLUMN "nhl"."player_games"."no" IS 'Jersey number of player in game';

COMMENT ON COLUMN "nhl"."player_games"."goals" IS 'Number of goals scored of player in game';

COMMENT ON COLUMN "nhl"."player_games"."assists" IS 'Number of assists by player in game';

COMMENT ON COLUMN "nhl"."player_games"."primary_assists" IS 'Number of primary assists by player in game';

COMMENT ON COLUMN "nhl"."player_games"."secondary_assists" IS 'Number of secondary assists by player in game';

COMMENT ON COLUMN "nhl"."player_games"."points" IS 'Number of points by player in game';

COMMENT ON COLUMN "nhl"."player_games"."plus_minus" IS 'Plus/minus rating for player';

COMMENT ON COLUMN "nhl"."player_games"."penalties" IS 'Number of penalties taken by player';

COMMENT ON COLUMN "nhl"."player_games"."pim" IS 'Penalty minutes for player';

COMMENT ON COLUMN "nhl"."player_games"."toi_overall" IS 'Overall time-on-ice';

COMMENT ON COLUMN "nhl"."player_games"."toi_pp" IS 'Power play time-on-ice';

COMMENT ON COLUMN "nhl"."player_games"."toi_sh" IS 'Shorthanded time-on-ice';

COMMENT ON COLUMN "nhl"."player_games"."toi_ev" IS 'Even strength time-on-ice';

COMMENT ON COLUMN "nhl"."player_games"."avg_shift" IS 'Average shift length';

COMMENT ON COLUMN "nhl"."player_games"."no_shifts" IS 'Number of shifts by player';

COMMENT ON COLUMN "nhl"."player_games"."shots_on_goal" IS 'Shots on goal by player';

COMMENT ON COLUMN "nhl"."player_games"."shots_blocked" IS 'Shots blocked for player';

COMMENT ON COLUMN "nhl"."player_games"."shots_missed" IS 'Shots missed by player';

COMMENT ON COLUMN "nhl"."player_games"."hits" IS 'Hits by player';

COMMENT ON COLUMN "nhl"."player_games"."giveaways" IS 'Giveaways by player';

COMMENT ON COLUMN "nhl"."player_games"."takeaways" IS 'Takeaways by player';

COMMENT ON COLUMN "nhl"."player_games"."blocks" IS 'Blocks by player';

COMMENT ON COLUMN "nhl"."player_games"."faceoffs_won" IS 'Faceoffs won by player';

COMMENT ON COLUMN "nhl"."player_games"."faceoffs_lost" IS 'Faceoffs lost by player';

COMMENT ON COLUMN "nhl"."player_games"."on_ice_shots_on_goal" IS 'Shots on goal with player on ice';

COMMENT ON COLUMN "nhl"."player_games"."on_ice_shots_blocked" IS 'Shots blocked with player on ice';

COMMENT ON COLUMN "nhl"."player_games"."on_ice_shots_missed" IS 'Missed shots with player on ice';

DROP TABLE IF EXISTS "nhl"."goalie_games" CASCADE;

CREATE TABLE "nhl"."goalie_games" (
	"goalie_game_id" int8 NOT NULL,
	"game_id" int4,
	"player_id" int4,
	"team_id" int4,
	"no" int2,
	"shots_against" int4,
	"goals_against" int4,
	"saves" int4,
	"en_goals" int2,
	"toi_overall" interval(0),
	"toi_pp" interval(0),
	"toi_sh" interval(0),
	"toi_ev" interval(0),
	"win" int2,
	"loss" int2,
	"otl" int2,
	"tie" int2,
	"regulation_tie" int2,
	"overtime_game" int2,
	"shootout_game" int2,
	"shutout" int2,
	"gaa" numeric,
	"save_pctg" numeric,
	CONSTRAINT "goalie_game_key" PRIMARY KEY("goalie_game_id")
);

CREATE TRIGGER "goalie_games_audit" AFTER INSERT OR UPDATE OR DELETE
	ON "nhl"."goalie_games" FOR EACH ROW
	EXECUTE PROCEDURE "nhl"."tr_log_actions"();


ALTER TABLE "nhl"."goalie_games" OWNER TO "nhl_user";

COMMENT ON TABLE "nhl"."goalie_games" IS 'National Hockey League goalies in a game';

COMMENT ON COLUMN "nhl"."goalie_games"."goalie_game_id" IS 'Unique goalie game ID as combination of game ID, player ID and team ID';

COMMENT ON COLUMN "nhl"."goalie_games"."game_id" IS 'Related game ID';

COMMENT ON COLUMN "nhl"."goalie_games"."player_id" IS 'Related player ID';

COMMENT ON COLUMN "nhl"."goalie_games"."team_id" IS 'Related team ID';

COMMENT ON COLUMN "nhl"."goalie_games"."no" IS 'Jersey number of goalie in a game';

COMMENT ON COLUMN "nhl"."goalie_games"."shots_against" IS 'Shots at goalie in a game';

COMMENT ON COLUMN "nhl"."goalie_games"."goals_against" IS 'Goals allowed by goalie in a game';

COMMENT ON COLUMN "nhl"."goalie_games"."saves" IS 'Saves made by goalie in a game';

COMMENT ON COLUMN "nhl"."goalie_games"."en_goals" IS 'Empty-net goals for goalie in a game';

COMMENT ON COLUMN "nhl"."goalie_games"."toi_overall" IS 'Overall time-on-ice';

COMMENT ON COLUMN "nhl"."goalie_games"."toi_pp" IS 'Power-play time-one-ice';

COMMENT ON COLUMN "nhl"."goalie_games"."toi_sh" IS 'Shorthanded time-on-ice';

COMMENT ON COLUMN "nhl"."goalie_games"."toi_ev" IS 'Even-strength time-on-ice';

COMMENT ON COLUMN "nhl"."goalie_games"."win" IS 'Win indicator for goalie in a game';

COMMENT ON COLUMN "nhl"."goalie_games"."loss" IS 'Loss indicator for goalie in a game';

COMMENT ON COLUMN "nhl"."goalie_games"."otl" IS 'Overtime loss indicator for goalie in a game';

COMMENT ON COLUMN "nhl"."goalie_games"."tie" IS 'Tie indicator for goalie in a game';

COMMENT ON COLUMN "nhl"."goalie_games"."regulation_tie" IS 'Regulation tie indicator for goalie in a game';

COMMENT ON COLUMN "nhl"."goalie_games"."overtime_game" IS 'Overtime game indicator for goalie in a game';

COMMENT ON COLUMN "nhl"."goalie_games"."shootout_game" IS 'Shootout game indicator for goalie in a game';

COMMENT ON COLUMN "nhl"."goalie_games"."shutout" IS 'Shutout indicator for goalie in a game';

COMMENT ON COLUMN "nhl"."goalie_games"."gaa" IS 'Goals-against-average for goalie in a game';

COMMENT ON COLUMN "nhl"."goalie_games"."save_pctg" IS 'Save percentage for goalie in a game';

DROP TABLE IF EXISTS "nhl"."shifts" CASCADE;

CREATE TABLE "nhl"."shifts" (
	"shift_id" int8 NOT NULL,
	"game_id" int4,
	"team_id" int4,
	"player_id" int4,
	"in_game_shift_cnt" int2,
	"period" int2,
	"start" interval(0),
	"end" interval(0),
	"duration" interval(2),
	CONSTRAINT "shift_key" PRIMARY KEY("shift_id")
);

CREATE INDEX "shift_game_id_player_id_in_game_shift_cnt_idx" ON "nhl"."shifts" USING BTREE (
	"game_id", 
	"player_id", 
	"in_game_shift_cnt"
);


CREATE TRIGGER "shifts_audit" AFTER INSERT OR UPDATE OR DELETE
	ON "nhl"."shifts" FOR EACH ROW
	EXECUTE PROCEDURE "nhl"."tr_log_actions"();


ALTER TABLE "nhl"."shifts" OWNER TO "nhl_user";

COMMENT ON TABLE "nhl"."shifts" IS 'Player game shifts in a National Hockey League game';

COMMENT ON COLUMN "nhl"."shifts"."shift_id" IS 'Unique shift ID as combination of game ID, team ID, jersey number and in game shift count';

COMMENT ON COLUMN "nhl"."shifts"."game_id" IS 'ID of the game in which the shift was played';

COMMENT ON COLUMN "nhl"."shifts"."team_id" IS 'ID of the team the shift was played for';

COMMENT ON COLUMN "nhl"."shifts"."player_id" IS 'ID of the player that played the shift';

COMMENT ON COLUMN "nhl"."shifts"."in_game_shift_cnt" IS 'In-game shift number for the given player';

COMMENT ON COLUMN "nhl"."shifts"."period" IS 'Period in which the shift was played';

COMMENT ON COLUMN "nhl"."shifts"."start" IS 'Start time of the shift';

COMMENT ON COLUMN "nhl"."shifts"."end" IS 'End time of the shift';

COMMENT ON COLUMN "nhl"."shifts"."duration" IS 'Duration of the shift';

DROP TABLE IF EXISTS "nhl"."events" CASCADE;

CREATE TABLE "nhl"."events" (
	"event_id" int8 NOT NULL,
	"game_id" int4,
	"in_game_event_cnt" int2,
	"type" varchar,
	"period" int2,
	"time" interval(0) NOT NULL,
	"num_situation" char(2),
	"road_on_ice" int4[],
	"home_on_ice" int4[],
	"road_score" int4,
	"home_score" int4,
	"x" int2,
	"y" int2,
	"stop_type" varchar,
	"road_goalie" int4,
	"home_goalie" int4,
	"raw_data" varchar(200),
	CONSTRAINT "event_key" PRIMARY KEY("event_id")
);

CREATE INDEX "event_game_id_in_game_event_id_idx" ON "nhl"."events" USING BTREE (
	"game_id", 
	"in_game_event_cnt"
);


CREATE TRIGGER "events_audit" AFTER INSERT OR UPDATE OR DELETE
	ON "nhl"."events" FOR EACH ROW
	EXECUTE PROCEDURE "nhl"."tr_log_actions"();


ALTER TABLE "nhl"."events" OWNER TO "nhl_user";

COMMENT ON TABLE "nhl"."events" IS 'Events in a National Hockey League game';

COMMENT ON COLUMN "nhl"."events"."event_id" IS 'ID of the event, a combination of game ID and in-game event count';

COMMENT ON COLUMN "nhl"."events"."game_id" IS 'ID of the game in which the event occurred';

COMMENT ON COLUMN "nhl"."events"."in_game_event_cnt" IS 'In-game event count';

COMMENT ON COLUMN "nhl"."events"."type" IS 'Type of the event';

COMMENT ON COLUMN "nhl"."events"."period" IS 'Period in which the event occurred';

COMMENT ON COLUMN "nhl"."events"."time" IS 'Timestamp of the event';

COMMENT ON COLUMN "nhl"."events"."num_situation" IS 'Numerical situation in consideration of the event';

COMMENT ON COLUMN "nhl"."events"."road_on_ice" IS 'Players of the road team being on-ice for the event';

COMMENT ON COLUMN "nhl"."events"."home_on_ice" IS 'Players of the home team being on-ice for the event';

COMMENT ON COLUMN "nhl"."events"."road_score" IS 'Game score for the road team';

COMMENT ON COLUMN "nhl"."events"."home_score" IS 'Game score for the home team';

COMMENT ON COLUMN "nhl"."events"."x" IS 'X coordinate of the event';

COMMENT ON COLUMN "nhl"."events"."y" IS 'Y coordinate of the event';

COMMENT ON COLUMN "nhl"."events"."stop_type" IS 'Stoppage type';

COMMENT ON COLUMN "nhl"."events"."road_goalie" IS 'Goaltender of the road team being on-ice for the event';

COMMENT ON COLUMN "nhl"."events"."home_goalie" IS 'Goaltender of the home team being on-ice for the event';

COMMENT ON COLUMN "nhl"."events"."raw_data" IS 'Raw event data from play-by-play report';

DROP TABLE IF EXISTS "nhl"."shots" CASCADE;

CREATE TABLE "nhl"."shots" (
	"shot_id" uuid NOT NULL,
	"event_id" int8,
	"team_id" int4,
	"player_id" int4,
	"zone" char(3),
	"goalie_team_id" int4,
	"goalie_id" int4,
	"shot_type" varchar,
	"distance" int2,
	"scored" bool DEFAULT False,
	"penalty_shot" bool,
	CONSTRAINT "shot_key" PRIMARY KEY("shot_id")
);

CREATE INDEX "shot_event_id_idx" ON "nhl"."shots" USING BTREE (
	"event_id"
);


CREATE TRIGGER "shots_audit" AFTER INSERT OR UPDATE OR DELETE
	ON "nhl"."shots" FOR EACH ROW
	EXECUTE PROCEDURE "nhl"."tr_log_actions"();


ALTER TABLE "nhl"."shots" OWNER TO "nhl_user";

COMMENT ON TABLE "nhl"."shots" IS 'Shots in a National Hockey League game';

COMMENT ON COLUMN "nhl"."shots"."shot_id" IS 'Unique shot ID';

COMMENT ON COLUMN "nhl"."shots"."event_id" IS 'Event ID of the shot';

COMMENT ON COLUMN "nhl"."shots"."team_id" IS 'ID of the team that took the shot';

COMMENT ON COLUMN "nhl"."shots"."player_id" IS 'ID of the player that took the shot';

COMMENT ON COLUMN "nhl"."shots"."zone" IS 'Zone where the shot was taken';

COMMENT ON COLUMN "nhl"."shots"."goalie_team_id" IS 'ID of the team that faced the shot';

COMMENT ON COLUMN "nhl"."shots"."goalie_id" IS 'ID of the goalie that faced the shot';

COMMENT ON COLUMN "nhl"."shots"."shot_type" IS 'Type of the shot';

COMMENT ON COLUMN "nhl"."shots"."distance" IS 'Distance from goal';

COMMENT ON COLUMN "nhl"."shots"."scored" IS 'Flag indicating whether a goal was scored on the shot';

COMMENT ON COLUMN "nhl"."shots"."penalty_shot" IS 'Flag indicating whether the shot was a penalty shot';

DROP TABLE IF EXISTS "nhl"."penalties" CASCADE;

CREATE TABLE "nhl"."penalties" (
	"penalty_id" uuid NOT NULL,
	"event_id" int8,
	"team_id" int4,
	"player_id" int4,
	"zone" char(3),
	"drawn_team_id" int4,
	"drawn_player_id" int4,
	"served_player_id" int4,
	"infraction" varchar(50),
	"pim" int2,
	CONSTRAINT "penalty_key" PRIMARY KEY("penalty_id")
);

CREATE INDEX "penalty_event_id_idx" ON "nhl"."penalties" USING BTREE (
	"event_id"
);


CREATE TRIGGER "penalties_audit" AFTER INSERT OR UPDATE OR DELETE
	ON "nhl"."penalties" FOR EACH ROW
	EXECUTE PROCEDURE "nhl"."tr_log_actions"();


ALTER TABLE "nhl"."penalties" OWNER TO "nhl_user";

COMMENT ON TABLE "nhl"."penalties" IS 'Penalties in a National Hockey League game';

COMMENT ON COLUMN "nhl"."penalties"."penalty_id" IS 'Unique penalty ID';

COMMENT ON COLUMN "nhl"."penalties"."event_id" IS 'Event ID of the penalty';

COMMENT ON COLUMN "nhl"."penalties"."team_id" IS 'ID of the team the penalty was given to';

COMMENT ON COLUMN "nhl"."penalties"."player_id" IS 'ID of the player the penalty was given to';

COMMENT ON COLUMN "nhl"."penalties"."zone" IS 'Zone in which the penalty occurred';

COMMENT ON COLUMN "nhl"."penalties"."drawn_team_id" IS 'ID of the team that drew the penalty';

COMMENT ON COLUMN "nhl"."penalties"."drawn_player_id" IS 'ID of the player that drew the penalty';

COMMENT ON COLUMN "nhl"."penalties"."served_player_id" IS 'ID of the player that served the penalty';

COMMENT ON COLUMN "nhl"."penalties"."infraction" IS 'Infraction that was penalized';

COMMENT ON COLUMN "nhl"."penalties"."pim" IS 'Penalty duration in minutes';

DROP TABLE IF EXISTS "nhl"."goals" CASCADE;

CREATE TABLE "nhl"."goals" (
	"goal_id" uuid NOT NULL,
	"event_id" int8,
	"team_id" int4,
	"player_id" int4,
	"goal_against_team_id" int4,
	"shot_id" uuid,
	"assist_1" int4,
	"assist_2" int4,
	"in_game_cnt" int4,
	"in_game_team_cnt" int4,
	"go_ahead_goal" bool,
	"tying_goal" bool,
	"empty_net_goal" bool,
	CONSTRAINT "goal_key" PRIMARY KEY("goal_id")
);

CREATE INDEX "goal_event_id_idx" ON "nhl"."goals" USING BTREE (
	"event_id"
);


CREATE TRIGGER "goals_audit" AFTER INSERT OR UPDATE OR DELETE
	ON "nhl"."goals" FOR EACH ROW
	EXECUTE PROCEDURE "nhl"."tr_log_actions"();


ALTER TABLE "nhl"."goals" OWNER TO "nhl_user";

COMMENT ON TABLE "nhl"."goals" IS 'Goals in a National Hockey League game';

COMMENT ON COLUMN "nhl"."goals"."goal_id" IS 'Unique goal ID';

COMMENT ON COLUMN "nhl"."goals"."event_id" IS 'Event ID of the goal';

COMMENT ON COLUMN "nhl"."goals"."team_id" IS 'ID of the team scoring the goal';

COMMENT ON COLUMN "nhl"."goals"."player_id" IS 'ID of the player scoring the goal';

COMMENT ON COLUMN "nhl"."goals"."goal_against_team_id" IS 'ID of the team the goal was scored on';

COMMENT ON COLUMN "nhl"."goals"."shot_id" IS 'ID of the shot the goal was scored on';

COMMENT ON COLUMN "nhl"."goals"."assist_1" IS 'ID of the player providing the primary assist';

COMMENT ON COLUMN "nhl"."goals"."assist_2" IS 'ID of the player providing the secondary assist';

COMMENT ON COLUMN "nhl"."goals"."in_game_cnt" IS 'Overall in-game count for the goal';

COMMENT ON COLUMN "nhl"."goals"."in_game_team_cnt" IS 'Team in-game count for the goal';

COMMENT ON COLUMN "nhl"."goals"."go_ahead_goal" IS 'Flag indicating whether the goal scored was a go-ahead goal';

COMMENT ON COLUMN "nhl"."goals"."tying_goal" IS 'Flag indicating whether the goal was tying a game';

COMMENT ON COLUMN "nhl"."goals"."empty_net_goal" IS 'Flag indicating whether the goal was scored into an empty net';

DROP TABLE IF EXISTS "nhl"."misses" CASCADE;

CREATE TABLE "nhl"."misses" (
	"miss_id" uuid NOT NULL,
	"event_id" int8,
	"team_id" int4,
	"player_id" int4,
	"zone" char(3),
	"goalie_team_id" int4,
	"goalie_id" int4,
	"shot_type" varchar,
	"miss_type" varchar,
	"distance" int2,
	"penalty_shot" bool,
	CONSTRAINT "miss_key" PRIMARY KEY("miss_id")
);

CREATE INDEX "miss_event_id_idx" ON "nhl"."misses" USING BTREE (
	"event_id"
);


CREATE TRIGGER "misses_audit" AFTER INSERT OR UPDATE OR DELETE
	ON "nhl"."misses" FOR EACH ROW
	EXECUTE PROCEDURE "nhl"."tr_log_actions"();


ALTER TABLE "nhl"."misses" OWNER TO "nhl_user";

COMMENT ON TABLE "nhl"."misses" IS 'Missed shots in a National Hockey League';

COMMENT ON COLUMN "nhl"."misses"."miss_id" IS 'Unique miss ID';

COMMENT ON COLUMN "nhl"."misses"."event_id" IS 'Event ID of the missed shot';

COMMENT ON COLUMN "nhl"."misses"."team_id" IS 'ID of the team missing the shot';

COMMENT ON COLUMN "nhl"."misses"."player_id" IS 'ID of the player that missed the shot';

COMMENT ON COLUMN "nhl"."misses"."zone" IS 'Zone where the shot was taken';

COMMENT ON COLUMN "nhl"."misses"."goalie_team_id" IS 'ID of the team having a goalie in net when the shot was missed';

COMMENT ON COLUMN "nhl"."misses"."goalie_id" IS 'ID of the goalie in net for the missed shot';

COMMENT ON COLUMN "nhl"."misses"."shot_type" IS 'Type of the missed shot';

COMMENT ON COLUMN "nhl"."misses"."miss_type" IS 'Type of the miss';

COMMENT ON COLUMN "nhl"."misses"."distance" IS 'Distance from goal';

COMMENT ON COLUMN "nhl"."misses"."penalty_shot" IS 'Flag indicating whether the missed shot was a penalty shot';

DROP TABLE IF EXISTS "nhl"."blocks" CASCADE;

CREATE TABLE "nhl"."blocks" (
	"block_id" uuid NOT NULL,
	"event_id" int8,
	"team_id" int4,
	"player_id" int4,
	"zone" char(3),
	"blocked_team_id" int4,
	"blocked_player_id" int4,
	"shot_type" varchar,
	CONSTRAINT "block_key" PRIMARY KEY("block_id")
);

CREATE INDEX "block_event_id_idx" ON "nhl"."blocks" USING BTREE (
	"event_id"
);


CREATE TRIGGER "blocks_audit" AFTER INSERT OR UPDATE OR DELETE
	ON "nhl"."blocks" FOR EACH ROW
	EXECUTE PROCEDURE "nhl"."tr_log_actions"();


ALTER TABLE "nhl"."blocks" OWNER TO "nhl_user";

COMMENT ON TABLE "nhl"."blocks" IS 'Blocked shots in a National Hockey League game';

COMMENT ON COLUMN "nhl"."blocks"."block_id" IS 'Unique block ID';

COMMENT ON COLUMN "nhl"."blocks"."event_id" IS 'Event ID of the block';

COMMENT ON COLUMN "nhl"."blocks"."team_id" IS 'ID of the team that had a shot blocked';

COMMENT ON COLUMN "nhl"."blocks"."player_id" IS 'ID of the player that blocked the shot';

COMMENT ON COLUMN "nhl"."blocks"."zone" IS 'Zone where the shot was blocked';

COMMENT ON COLUMN "nhl"."blocks"."blocked_team_id" IS 'ID of the team that had a shot blocked';

COMMENT ON COLUMN "nhl"."blocks"."blocked_player_id" IS 'ID of the player whose shot was blocked';

COMMENT ON COLUMN "nhl"."blocks"."shot_type" IS 'Type of the blocked shot';

DROP TABLE IF EXISTS "nhl"."faceoffs" CASCADE;

CREATE TABLE "nhl"."faceoffs" (
	"faceoff_id" uuid NOT NULL,
	"event_id" int8,
	"team_id" int4,
	"player_id" int4,
	"zone" char(3),
	"faceoff_lost_team_id" int4,
	"faceoff_lost_player_id" int4,
	"faceoff_lost_zone" char(3),
	CONSTRAINT "faceoff_key" PRIMARY KEY("faceoff_id")
);

CREATE INDEX "faceoff_event_id_idx" ON "nhl"."faceoffs" USING BTREE (
	"event_id"
);


CREATE TRIGGER "faceoffs_audit" AFTER INSERT OR UPDATE OR DELETE
	ON "nhl"."faceoffs" FOR EACH ROW
	EXECUTE PROCEDURE "nhl"."tr_log_actions"();


ALTER TABLE "nhl"."faceoffs" OWNER TO "nhl_user";

COMMENT ON TABLE "nhl"."faceoffs" IS 'Faceoffs in a National Hockey League game';

COMMENT ON COLUMN "nhl"."faceoffs"."faceoff_id" IS 'Unique ID of the faceoff event';

COMMENT ON COLUMN "nhl"."faceoffs"."event_id" IS 'Event ID of the faceoff';

COMMENT ON COLUMN "nhl"."faceoffs"."team_id" IS 'ID of the team that won the faceoff';

COMMENT ON COLUMN "nhl"."faceoffs"."player_id" IS 'ID of the player that won the faceoff';

COMMENT ON COLUMN "nhl"."faceoffs"."zone" IS 'Zone where the faceoff took place for the winning team';

COMMENT ON COLUMN "nhl"."faceoffs"."faceoff_lost_team_id" IS 'ID of the team that lost the faceoff';

COMMENT ON COLUMN "nhl"."faceoffs"."faceoff_lost_player_id" IS 'ID of the player that lost the faceoff';

COMMENT ON COLUMN "nhl"."faceoffs"."faceoff_lost_zone" IS 'Zone where the faceoff took place for the losing team';

DROP TABLE IF EXISTS "nhl"."hits" CASCADE;

CREATE TABLE "nhl"."hits" (
	"hit_id" uuid NOT NULL,
	"event_id" int8,
	"team_id" int4,
	"player_id" int4,
	"zone" char(3),
	"hit_taken_team_id" int4,
	"hit_taken_player_id" int4,
	CONSTRAINT "hit_key" PRIMARY KEY("hit_id")
);

CREATE INDEX "hit_event_id_idx" ON "nhl"."hits" USING BTREE (
	"event_id"
);


CREATE TRIGGER "hits_audit" AFTER INSERT OR UPDATE OR DELETE
	ON "nhl"."hits" FOR EACH ROW
	EXECUTE PROCEDURE "nhl"."tr_log_actions"();


ALTER TABLE "nhl"."hits" OWNER TO "nhl_user";

COMMENT ON TABLE "nhl"."hits" IS 'Hits in a National Hockey League game';

COMMENT ON COLUMN "nhl"."hits"."hit_id" IS 'Unique hit ID';

COMMENT ON COLUMN "nhl"."hits"."event_id" IS 'Event ID of the hit';

COMMENT ON COLUMN "nhl"."hits"."team_id" IS 'ID of the team that executed the hit';

COMMENT ON COLUMN "nhl"."hits"."player_id" IS 'ID of the player executing the hit';

COMMENT ON COLUMN "nhl"."hits"."zone" IS 'Zone where the hit was executed';

COMMENT ON COLUMN "nhl"."hits"."hit_taken_team_id" IS 'ID of the team taking the hit';

COMMENT ON COLUMN "nhl"."hits"."hit_taken_player_id" IS 'ID of the player taking the hit';

DROP TABLE IF EXISTS "nhl"."giveaways" CASCADE;

CREATE TABLE "nhl"."giveaways" (
	"giveaway_id" uuid NOT NULL,
	"event_id" int8,
	"team_id" int4,
	"player_id" int4,
	"zone" char(3),
	"given_to_team_id" int4,
	CONSTRAINT "giveaway_key" PRIMARY KEY("giveaway_id")
);

CREATE INDEX "giveaway_event_id_idx" ON "nhl"."giveaways" USING BTREE (
	"event_id"
);


CREATE TRIGGER "giveaways_audit" AFTER INSERT OR UPDATE OR DELETE
	ON "nhl"."giveaways" FOR EACH ROW
	EXECUTE PROCEDURE "nhl"."tr_log_actions"();


ALTER TABLE "nhl"."giveaways" OWNER TO "nhl_user";

COMMENT ON TABLE "nhl"."giveaways" IS 'Giveaways in a National Hockey League game';

COMMENT ON COLUMN "nhl"."giveaways"."giveaway_id" IS 'Unique giveaway ID';

COMMENT ON COLUMN "nhl"."giveaways"."event_id" IS 'Event ID of the giveaway';

COMMENT ON COLUMN "nhl"."giveaways"."team_id" IS 'ID of the team giving the puck away';

COMMENT ON COLUMN "nhl"."giveaways"."player_id" IS 'ID of the player giving the puck away';

COMMENT ON COLUMN "nhl"."giveaways"."zone" IS 'Zone where the giveaway occurred';

COMMENT ON COLUMN "nhl"."giveaways"."given_to_team_id" IS 'ID of the team the puck was given to';

DROP TABLE IF EXISTS "nhl"."takeaways" CASCADE;

CREATE TABLE "nhl"."takeaways" (
	"takeaway_id" uuid NOT NULL,
	"event_id" int8,
	"team_id" int4,
	"player_id" int4,
	"zone" char(3),
	"taken_from_team_id" int4,
	CONSTRAINT "takeaway_key" PRIMARY KEY("takeaway_id")
);

CREATE INDEX "takeaway_event_id_idx" ON "nhl"."takeaways" USING BTREE (
	"event_id"
);


CREATE TRIGGER "takeaways_audit" AFTER INSERT OR UPDATE OR DELETE
	ON "nhl"."takeaways" FOR EACH ROW
	EXECUTE PROCEDURE "nhl"."tr_log_actions"();


ALTER TABLE "nhl"."takeaways" OWNER TO "nhl_user";

COMMENT ON TABLE "nhl"."takeaways" IS 'Takeaways in a National Hockey League game';

COMMENT ON COLUMN "nhl"."takeaways"."takeaway_id" IS 'Unique takeaway ID';

COMMENT ON COLUMN "nhl"."takeaways"."event_id" IS 'Event ID of the takeaway';

COMMENT ON COLUMN "nhl"."takeaways"."team_id" IS 'ID of the team taking away the puck';

COMMENT ON COLUMN "nhl"."takeaways"."player_id" IS 'ID of the player taking away the puck';

COMMENT ON COLUMN "nhl"."takeaways"."zone" IS 'Zone where the takeaway occurred';

COMMENT ON COLUMN "nhl"."takeaways"."taken_from_team_id" IS 'ID of the team the puck was taken away from';

DROP TABLE IF EXISTS "nhl"."team_games" CASCADE;

CREATE TABLE "nhl"."team_games" (
	"team_game_id" int8 NOT NULL,
	"game_id" int4,
	"team_id" int4,
	"home_road_type" varchar(4),
	"score" int2 NOT NULL DEFAULT 0,
	"score_against" int2 NOT NULL DEFAULT 0,
	"goals_for_1st" int2 NOT NULL DEFAULT 0,
	"goals_against_1st" int2 NOT NULL DEFAULT 0,
	"goals_for_2nd" int2 NOT NULL DEFAULT 0,
	"goals_against_2nd" int2 NOT NULL DEFAULT 0,
	"goals_for_3rd" int2 NOT NULL DEFAULT 0,
	"goals_against_3rd" int2 NOT NULL DEFAULT 0,
	"goals_for" int2 NOT NULL DEFAULT 0,
	"empty_net_goals_for" int2 NOT NULL DEFAULT 0,
	"goals_against" int2 NOT NULL DEFAULT 0,
	"empty_net_goals_against" int2 NOT NULL DEFAULT 0,
	"win" int2 NOT NULL DEFAULT 0,
	"regulation_win" int2 NOT NULL DEFAULT 0,
	"overtime_win" int2 NOT NULL DEFAULT 0,
	"shootout_win" int2 NOT NULL DEFAULT 0,
	"loss" int2 NOT NULL DEFAULT 0,
	"regulation_loss" int2 NOT NULL DEFAULT 0,
	"overtime_loss" int2 NOT NULL DEFAULT 0,
	"shootout_loss" int2 NOT NULL DEFAULT 0,
	"tie" int2 NOT NULL DEFAULT 0,
	"pp_overall" int2 NOT NULL DEFAULT 0,
	"pp_time_overall" interval(0),
	"pp_5v4" int2 NOT NULL DEFAULT 0,
	"pp_time_5v4" interval(0),
	"pp_4v3" int2 NOT NULL DEFAULT 0,
	"pp_time_4v3" interval(0),
	"pp_5v3" int2 NOT NULL DEFAULT 0,
	"pp_time_5v3" interval(0),
	"shots_for" int2 NOT NULL DEFAULT 0,
	"shots_against" int2 NOT NULL DEFAULT 0,
	"shots_for_1st" int2 NOT NULL DEFAULT 0,
	"shots_against_1st" int2 NOT NULL DEFAULT 0,
	"shots_for_2nd" int2 NOT NULL DEFAULT 0,
	"shots_against_2nd" int2 NOT NULL DEFAULT 0,
	"shots_for_3rd" int2 NOT NULL DEFAULT 0,
	"shots_against_3rd" int2 NOT NULL DEFAULT 0,
	"shots_for_ot" int2 DEFAULT NULL,
	"shots_against_ot" int2 DEFAULT NULL,
	"so_attempts" int2 DEFAULT NULL,
	"so_goals" int2 DEFAULT NULL,
	"penalties" int2 NOT NULL,
	"pim" int4 NOT NULL DEFAULT 0,
	"points" int2 NOT NULL DEFAULT 0,
	CONSTRAINT "team_game_key" PRIMARY KEY("team_game_id")
);

CREATE TRIGGER "team_games_audit" AFTER INSERT OR UPDATE OR DELETE
	ON "nhl"."team_games" FOR EACH ROW
	EXECUTE PROCEDURE "nhl"."tr_log_actions"();


ALTER TABLE "nhl"."team_games" OWNER TO "nhl_user";

COMMENT ON TABLE "nhl"."team_games" IS 'National Hockey League teams in a game';

COMMENT ON COLUMN "nhl"."team_games"."team_game_id" IS 'Unique team game ID as combination of game ID and team ID';

COMMENT ON COLUMN "nhl"."team_games"."game_id" IS 'Related game ID';

COMMENT ON COLUMN "nhl"."team_games"."team_id" IS 'Related team ID';

COMMENT ON COLUMN "nhl"."team_games"."home_road_type" IS 'Code indicating home or road game';

COMMENT ON COLUMN "nhl"."team_games"."score" IS 'Final score';

COMMENT ON COLUMN "nhl"."team_games"."score_against" IS 'Final score against';

COMMENT ON COLUMN "nhl"."team_games"."goals_for_1st" IS 'Goals scored in 1st period';

COMMENT ON COLUMN "nhl"."team_games"."goals_against_1st" IS 'Goals allowed in 1st period';

COMMENT ON COLUMN "nhl"."team_games"."goals_for_2nd" IS 'Goals scored in 2nd period';

COMMENT ON COLUMN "nhl"."team_games"."goals_against_2nd" IS 'Goals allowed in 2nd period';

COMMENT ON COLUMN "nhl"."team_games"."goals_for_3rd" IS 'Goals scored in 3rd period';

COMMENT ON COLUMN "nhl"."team_games"."goals_against_3rd" IS 'Goals allowed in 3rd period';

COMMENT ON COLUMN "nhl"."team_games"."goals_for" IS 'Goals scored overall';

COMMENT ON COLUMN "nhl"."team_games"."empty_net_goals_for" IS 'Empty-net goals scored';

COMMENT ON COLUMN "nhl"."team_games"."goals_against" IS 'Goals allowed overall';

COMMENT ON COLUMN "nhl"."team_games"."empty_net_goals_against" IS 'Empty-net goals allowed';

COMMENT ON COLUMN "nhl"."team_games"."win" IS 'Binary indicating a win';

COMMENT ON COLUMN "nhl"."team_games"."regulation_win" IS 'Binary indicating a win in regulation time';

COMMENT ON COLUMN "nhl"."team_games"."overtime_win" IS 'Binary indicating a win in overtime';

COMMENT ON COLUMN "nhl"."team_games"."shootout_win" IS 'Binary indicating a win in a shootout';

COMMENT ON COLUMN "nhl"."team_games"."loss" IS 'Binary indicating a loss';

COMMENT ON COLUMN "nhl"."team_games"."regulation_loss" IS 'Binary indicating a loss in regulation time';

COMMENT ON COLUMN "nhl"."team_games"."overtime_loss" IS 'Binary indicating a loss in overtime';

COMMENT ON COLUMN "nhl"."team_games"."shootout_loss" IS 'Binary indicating a loss in a shootout';

COMMENT ON COLUMN "nhl"."team_games"."tie" IS 'Binary indicating a tie';

COMMENT ON COLUMN "nhl"."team_games"."pp_overall" IS 'Power-play opportunities overall';

COMMENT ON COLUMN "nhl"."team_games"."pp_time_overall" IS 'Power-play time overall';

COMMENT ON COLUMN "nhl"."team_games"."pp_5v4" IS '5-on-4 power-play opportunities';

COMMENT ON COLUMN "nhl"."team_games"."pp_time_5v4" IS '5-on-4 power-play time';

COMMENT ON COLUMN "nhl"."team_games"."pp_4v3" IS '4-on-3 power-play opportunities';

COMMENT ON COLUMN "nhl"."team_games"."pp_time_4v3" IS '4-on-3 power-play time';

COMMENT ON COLUMN "nhl"."team_games"."pp_5v3" IS '5-on-3 power-play opportunities';

COMMENT ON COLUMN "nhl"."team_games"."pp_time_5v3" IS '5-on-3 power-play time';

COMMENT ON COLUMN "nhl"."team_games"."shots_for" IS 'Shots on goal overall';

COMMENT ON COLUMN "nhl"."team_games"."shots_against" IS 'Shots on goal allowed overall';

COMMENT ON COLUMN "nhl"."team_games"."shots_for_1st" IS 'Shots on goal in 1st period';

COMMENT ON COLUMN "nhl"."team_games"."shots_against_1st" IS 'Shots on goal allowed in 1st period';

COMMENT ON COLUMN "nhl"."team_games"."shots_for_2nd" IS 'Shots on goal in 2nd period';

COMMENT ON COLUMN "nhl"."team_games"."shots_against_2nd" IS 'Shots on goal allowed in 2nd period';

COMMENT ON COLUMN "nhl"."team_games"."shots_for_3rd" IS 'Shots on goal in 3rd period';

COMMENT ON COLUMN "nhl"."team_games"."shots_against_3rd" IS 'Shots on goal allowed in 3rd period';

COMMENT ON COLUMN "nhl"."team_games"."shots_for_ot" IS 'Shots on goal in overtime period(s)';

COMMENT ON COLUMN "nhl"."team_games"."shots_against_ot" IS 'Shots on goal allowed in overtime period(s)';

COMMENT ON COLUMN "nhl"."team_games"."so_attempts" IS 'Shootout attempts';

COMMENT ON COLUMN "nhl"."team_games"."so_goals" IS 'Shootout goals';

COMMENT ON COLUMN "nhl"."team_games"."penalties" IS 'Number of penalties assessed';

COMMENT ON COLUMN "nhl"."team_games"."pim" IS 'Number of penalty minutes assessed';

COMMENT ON COLUMN "nhl"."team_games"."points" IS 'Points gained in game';

DROP TABLE IF EXISTS "nhl"."shootout_attempts" CASCADE;

CREATE TABLE "nhl"."shootout_attempts" (
	"shootout_attempt_id" uuid NOT NULL,
	"event_id" int8,
	"team_id" int4,
	"player_id" int4,
	"zone" char(3),
	"goalie_team_id" int4,
	"goalie_id" int4,
	"attempt_type" varchar(4),
	"shot_type" varchar,
	"miss_type" varchar,
	"distance" int2,
	"on_goal" bool,
	"scored" bool,
	CONSTRAINT "shootout_key" PRIMARY KEY("shootout_attempt_id")
);

CREATE INDEX "shootout_attempt_event_id_idx" ON "nhl"."shootout_attempts" USING BTREE (
	"event_id"
);


CREATE TRIGGER "shootout_attempts_audit" AFTER INSERT OR UPDATE OR DELETE
	ON "nhl"."shootout_attempts" FOR EACH ROW
	EXECUTE PROCEDURE "nhl"."tr_log_actions"();


ALTER TABLE "nhl"."shootout_attempts" OWNER TO "nhl_user";

COMMENT ON COLUMN "nhl"."shootout_attempts"."shootout_attempt_id" IS 'Unique ID for shootout attempt';

COMMENT ON COLUMN "nhl"."shootout_attempts"."event_id" IS 'Event ID of the shootout attempt';

COMMENT ON COLUMN "nhl"."shootout_attempts"."team_id" IS 'ID of the team executing the shootout attempt';

COMMENT ON COLUMN "nhl"."shootout_attempts"."player_id" IS 'ID of the player executing the shootout attempt';

COMMENT ON COLUMN "nhl"."shootout_attempts"."zone" IS 'Zone where the shootout attempt was taken';

COMMENT ON COLUMN "nhl"."shootout_attempts"."goalie_team_id" IS 'ID of the team defending the shootout attempt';

COMMENT ON COLUMN "nhl"."shootout_attempts"."goalie_id" IS 'ID of the goaltender defending the shootout attempt';

COMMENT ON COLUMN "nhl"."shootout_attempts"."attempt_type" IS 'Result of the shootout attempt';

COMMENT ON COLUMN "nhl"."shootout_attempts"."shot_type" IS 'Type of the shot';

COMMENT ON COLUMN "nhl"."shootout_attempts"."miss_type" IS 'Type of the miss';

COMMENT ON COLUMN "nhl"."shootout_attempts"."distance" IS 'Distance from which the shootout attempt was taken';

COMMENT ON COLUMN "nhl"."shootout_attempts"."on_goal" IS 'Flag indicating whether the shootout attempt was a shot on goal';

COMMENT ON COLUMN "nhl"."shootout_attempts"."scored" IS 'Flag indicating whether the shootout attempt was succesful';

DROP TABLE IF EXISTS "nhl"."shot_attempts" CASCADE;

CREATE TABLE "nhl"."shot_attempts" (
	"shot_attempt_id" uuid NOT NULL,
	"game_id" int4,
	"team_id" int4,
	"event_id" int8,
	"player_id" int4,
	"shot_attempt_type" char(1) NOT NULL,
	"plus_minus" int2,
	"num_situation" char(2),
	"plr_situation" varchar(5),
	"actual" bool,
	"score_diff" int2,
	CONSTRAINT "type_check" CHECK(shot_attempt_type in ('S', 'M', 'B')),
	CONSTRAINT "shot_attempt_key" PRIMARY KEY("shot_attempt_id")
);

CREATE INDEX "shot_attempt_game_id_event_id_player_id_idx" ON "nhl"."shot_attempts" USING BTREE (
	"game_id", 
	"event_id", 
	"player_id"
);


CREATE INDEX "shot_attempt_event_id_player_id_idx" ON "nhl"."shot_attempts" USING BTREE (
	"event_id", 
	"player_id"
);


CREATE TRIGGER "shot_attempts_audit" AFTER INSERT OR UPDATE OR DELETE
	ON "nhl"."shot_attempts" FOR EACH ROW
	EXECUTE PROCEDURE "nhl"."tr_log_actions"();


ALTER TABLE "nhl"."shot_attempts" OWNER TO "nhl_user";

COMMENT ON COLUMN "nhl"."shot_attempts"."game_id" IS 'Related game ID';

COMMENT ON COLUMN "nhl"."shot_attempts"."team_id" IS 'Related team ID';

COMMENT ON COLUMN "nhl"."shot_attempts"."event_id" IS 'Related event ID';

COMMENT ON COLUMN "nhl"."shot_attempts"."player_id" IS 'Related player ID';

COMMENT ON COLUMN "nhl"."shot_attempts"."shot_attempt_type" IS 'Type of the shot attempt, e.g. (M)iss, (B)lock or (S)hot on Goal';

COMMENT ON COLUMN "nhl"."shot_attempts"."plus_minus" IS 'Indicator whether the current one is a for or against event';

COMMENT ON COLUMN "nhl"."shot_attempts"."num_situation" IS 'Official numerical situation at the time of the shot attempt event, e.g. EV, PP or SH';

COMMENT ON COLUMN "nhl"."shot_attempts"."plr_situation" IS 'Actual numerical situation at the time of the shot attempt event, e.g. 5v5, 5v4, 6v5 etc.';

COMMENT ON COLUMN "nhl"."shot_attempts"."actual" IS 'Indicator whether the current entry shows the player actual contributing the shot attempt';

COMMENT ON COLUMN "nhl"."shot_attempts"."score_diff" IS 'Score differential at the time of the shot attempt event as registered by the current team';


ALTER TABLE "nhl"."player_seasons" ADD CONSTRAINT "player_seasons_to_players" FOREIGN KEY ("player_id")
	REFERENCES "nhl"."players"("player_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."player_seasons" ADD CONSTRAINT "player_seasons_to_teams" FOREIGN KEY ("team_id")
	REFERENCES "nhl"."teams"("team_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."goalie_seasons" ADD CONSTRAINT "goalie_seasons_to_players" FOREIGN KEY ("player_id")
	REFERENCES "nhl"."players"("player_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."goalie_seasons" ADD CONSTRAINT "goalie_seasons_to_teams" FOREIGN KEY ("team_id")
	REFERENCES "nhl"."teams"("team_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."player_data" ADD CONSTRAINT "player_data_to_players" FOREIGN KEY ("player_id")
	REFERENCES "nhl"."players"("player_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."contracts" ADD CONSTRAINT "contracts_to_teams" FOREIGN KEY ("signing_team_id")
	REFERENCES "nhl"."teams"("team_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."contracts" ADD CONSTRAINT "contracts_to_players" FOREIGN KEY ("player_id")
	REFERENCES "nhl"."players"("player_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."contract_years" ADD CONSTRAINT "contract_years_to_contracts" FOREIGN KEY ("contract_id")
	REFERENCES "nhl"."contracts"("contract_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."contract_years" ADD CONSTRAINT "contract_years_to_players" FOREIGN KEY ("player_id")
	REFERENCES "nhl"."players"("player_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."buyouts" ADD CONSTRAINT "buyouts_to_contracts" FOREIGN KEY ("contract_id")
	REFERENCES "nhl"."contracts"("contract_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."buyouts" ADD CONSTRAINT "buyouts_to_players" FOREIGN KEY ("player_id")
	REFERENCES "nhl"."players"("player_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."buyouts" ADD CONSTRAINT "buyouts_to_teams" FOREIGN KEY ("buyout_team_id")
	REFERENCES "nhl"."teams"("team_id")
	MATCH SIMPLE
	ON DELETE NO ACTION
	ON UPDATE NO ACTION
	NOT DEFERRABLE;

ALTER TABLE "nhl"."buyout_years" ADD CONSTRAINT "nhl_buyout_years_to_buyouts" FOREIGN KEY ("buyout_id")
	REFERENCES "nhl"."buyouts"("buyout_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."buyout_years" ADD CONSTRAINT "buyout_years_to_players" FOREIGN KEY ("player_id")
	REFERENCES "nhl"."players"("player_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."player_drafts" ADD CONSTRAINT "player_drafts_to_teams" FOREIGN KEY ("team_id")
	REFERENCES "nhl"."teams"("team_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."player_drafts" ADD CONSTRAINT "player_drafts_to_players" FOREIGN KEY ("player_id")
	REFERENCES "nhl"."players"("player_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."games" ADD CONSTRAINT "road_games_to_teams" FOREIGN KEY ("road_team_id")
	REFERENCES "nhl"."teams"("team_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."games" ADD CONSTRAINT "home_games_to_teams" FOREIGN KEY ("home_team_id")
	REFERENCES "nhl"."teams"("team_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."games" ADD CONSTRAINT "game_1st_star_to_players" FOREIGN KEY ("star_1")
	REFERENCES "nhl"."players"("player_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."games" ADD CONSTRAINT "game_2nd_star_to_players" FOREIGN KEY ("star_2")
	REFERENCES "nhl"."players"("player_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."games" ADD CONSTRAINT "game_3rd_star_to_players" FOREIGN KEY ("star_3")
	REFERENCES "nhl"."players"("player_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."player_games" ADD CONSTRAINT "player_games_to_games" FOREIGN KEY ("game_id")
	REFERENCES "nhl"."games"("game_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."player_games" ADD CONSTRAINT "player_games_to_players" FOREIGN KEY ("player_id")
	REFERENCES "nhl"."players"("player_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."player_games" ADD CONSTRAINT "player_games_to_teams" FOREIGN KEY ("team_id")
	REFERENCES "nhl"."teams"("team_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."goalie_games" ADD CONSTRAINT "nhl_goalie_games_to_teams" FOREIGN KEY ("team_id")
	REFERENCES "nhl"."teams"("team_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."goalie_games" ADD CONSTRAINT "nhl_goalie_games_to_players" FOREIGN KEY ("player_id")
	REFERENCES "nhl"."players"("player_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."goalie_games" ADD CONSTRAINT "nhl_goalie_games_to_games" FOREIGN KEY ("game_id")
	REFERENCES "nhl"."games"("game_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."shifts" ADD CONSTRAINT "shifts_to_players" FOREIGN KEY ("player_id")
	REFERENCES "nhl"."players"("player_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."shifts" ADD CONSTRAINT "shifts_to_teams" FOREIGN KEY ("team_id")
	REFERENCES "nhl"."teams"("team_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."shifts" ADD CONSTRAINT "shifts_to_games" FOREIGN KEY ("game_id")
	REFERENCES "nhl"."games"("game_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."events" ADD CONSTRAINT "events_to_games" FOREIGN KEY ("game_id")
	REFERENCES "nhl"."games"("game_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."shots" ADD CONSTRAINT "shots_to_teams" FOREIGN KEY ("team_id")
	REFERENCES "nhl"."teams"("team_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."shots" ADD CONSTRAINT "shots_to_players" FOREIGN KEY ("player_id")
	REFERENCES "nhl"."players"("player_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."shots" ADD CONSTRAINT "shots_at_to_teams" FOREIGN KEY ("goalie_team_id")
	REFERENCES "nhl"."teams"("team_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."shots" ADD CONSTRAINT "shots_goalies_to_players" FOREIGN KEY ("goalie_id")
	REFERENCES "nhl"."players"("player_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."shots" ADD CONSTRAINT "shots_to_events" FOREIGN KEY ("event_id")
	REFERENCES "nhl"."events"("event_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."penalties" ADD CONSTRAINT "penalties_to_events" FOREIGN KEY ("event_id")
	REFERENCES "nhl"."events"("event_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."penalties" ADD CONSTRAINT "penalties_to_teams" FOREIGN KEY ("team_id")
	REFERENCES "nhl"."teams"("team_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."penalties" ADD CONSTRAINT "penalties_to_players" FOREIGN KEY ("player_id")
	REFERENCES "nhl"."players"("player_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."goals" ADD CONSTRAINT "goals_to_events" FOREIGN KEY ("event_id")
	REFERENCES "nhl"."events"("event_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."goals" ADD CONSTRAINT "goals_to_teams" FOREIGN KEY ("team_id")
	REFERENCES "nhl"."teams"("team_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."goals" ADD CONSTRAINT "goals_to_players" FOREIGN KEY ("player_id")
	REFERENCES "nhl"."players"("player_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."goals" ADD CONSTRAINT "goals_against_to_teams" FOREIGN KEY ("goal_against_team_id")
	REFERENCES "nhl"."teams"("team_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."goals" ADD CONSTRAINT "goals_to_shots" FOREIGN KEY ("shot_id")
	REFERENCES "nhl"."shots"("shot_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."goals" ADD CONSTRAINT "assists_1_to_players" FOREIGN KEY ("assist_1")
	REFERENCES "nhl"."players"("player_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."goals" ADD CONSTRAINT "assists_2_to_players" FOREIGN KEY ("assist_2")
	REFERENCES "nhl"."players"("player_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."misses" ADD CONSTRAINT "misses_to_events" FOREIGN KEY ("event_id")
	REFERENCES "nhl"."events"("event_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."misses" ADD CONSTRAINT "misses_to_teams" FOREIGN KEY ("team_id")
	REFERENCES "nhl"."teams"("team_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."misses" ADD CONSTRAINT "misses_to_players" FOREIGN KEY ("player_id")
	REFERENCES "nhl"."players"("player_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."misses" ADD CONSTRAINT "miss_goalies_to_teams" FOREIGN KEY ("goalie_team_id")
	REFERENCES "nhl"."teams"("team_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."misses" ADD CONSTRAINT "miss_goalies_to_players" FOREIGN KEY ("goalie_id")
	REFERENCES "nhl"."players"("player_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."blocks" ADD CONSTRAINT "blocks_to_events" FOREIGN KEY ("event_id")
	REFERENCES "nhl"."events"("event_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."blocks" ADD CONSTRAINT "blocks_to_teams" FOREIGN KEY ("team_id")
	REFERENCES "nhl"."teams"("team_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."blocks" ADD CONSTRAINT "blocked_to_teams" FOREIGN KEY ("blocked_team_id")
	REFERENCES "nhl"."teams"("team_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."blocks" ADD CONSTRAINT "blocked_to_players" FOREIGN KEY ("blocked_player_id")
	REFERENCES "nhl"."players"("player_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."blocks" ADD CONSTRAINT "blocks_to_players" FOREIGN KEY ("player_id")
	REFERENCES "nhl"."players"("player_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."faceoffs" ADD CONSTRAINT "faceoffs_to_events" FOREIGN KEY ("event_id")
	REFERENCES "nhl"."events"("event_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."faceoffs" ADD CONSTRAINT "faceoffs_to_teams" FOREIGN KEY ("team_id")
	REFERENCES "nhl"."teams"("team_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."faceoffs" ADD CONSTRAINT "faceoffs_to_players" FOREIGN KEY ("player_id")
	REFERENCES "nhl"."players"("player_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."faceoffs" ADD CONSTRAINT "faceoffs_lost_to_teams" FOREIGN KEY ("faceoff_lost_team_id")
	REFERENCES "nhl"."teams"("team_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."faceoffs" ADD CONSTRAINT "faceoffs_to_players0" FOREIGN KEY ("player_id")
	REFERENCES "nhl"."players"("player_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."faceoffs" ADD CONSTRAINT "faceoffs_lost_to_players" FOREIGN KEY ("faceoff_lost_player_id")
	REFERENCES "nhl"."players"("player_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."hits" ADD CONSTRAINT "hits_to_events" FOREIGN KEY ("event_id")
	REFERENCES "nhl"."events"("event_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."hits" ADD CONSTRAINT "hits_to_teams" FOREIGN KEY ("team_id")
	REFERENCES "nhl"."teams"("team_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."hits" ADD CONSTRAINT "hits_taken_to_teams" FOREIGN KEY ("hit_taken_team_id")
	REFERENCES "nhl"."teams"("team_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."hits" ADD CONSTRAINT "hits_to_players" FOREIGN KEY ("player_id")
	REFERENCES "nhl"."players"("player_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."hits" ADD CONSTRAINT "hits_taken_to_players" FOREIGN KEY ("hit_taken_player_id")
	REFERENCES "nhl"."players"("player_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."giveaways" ADD CONSTRAINT "giveaways_to_events" FOREIGN KEY ("event_id")
	REFERENCES "nhl"."events"("event_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."giveaways" ADD CONSTRAINT "giveaways_to_teams" FOREIGN KEY ("team_id")
	REFERENCES "nhl"."teams"("team_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."giveaways" ADD CONSTRAINT "giveaways_to_players" FOREIGN KEY ("player_id")
	REFERENCES "nhl"."players"("player_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."giveaways" ADD CONSTRAINT "giveaways_received_to_teams" FOREIGN KEY ("given_to_team_id")
	REFERENCES "nhl"."teams"("team_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."takeaways" ADD CONSTRAINT "takeaways_to_events" FOREIGN KEY ("event_id")
	REFERENCES "nhl"."events"("event_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."takeaways" ADD CONSTRAINT "takeaways_to_teams" FOREIGN KEY ("team_id")
	REFERENCES "nhl"."teams"("team_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."takeaways" ADD CONSTRAINT "takeaways_to_players" FOREIGN KEY ("player_id")
	REFERENCES "nhl"."players"("player_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."takeaways" ADD CONSTRAINT "takeaways_from_to_teams" FOREIGN KEY ("taken_from_team_id")
	REFERENCES "nhl"."teams"("team_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."team_games" ADD CONSTRAINT "team_games_to_teams" FOREIGN KEY ("team_id")
	REFERENCES "nhl"."teams"("team_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."team_games" ADD CONSTRAINT "team_games_to_games" FOREIGN KEY ("game_id")
	REFERENCES "nhl"."games"("game_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."shootout_attempts" ADD CONSTRAINT "shootout_attempts_to_teams" FOREIGN KEY ("team_id")
	REFERENCES "nhl"."teams"("team_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."shootout_attempts" ADD CONSTRAINT "shootout_attempts_to_events" FOREIGN KEY ("event_id")
	REFERENCES "nhl"."events"("event_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."shootout_attempts" ADD CONSTRAINT "shootout_attempts_to_players" FOREIGN KEY ("player_id")
	REFERENCES "nhl"."players"("player_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."shootout_attempts" ADD CONSTRAINT "shootout_attempts_at_to_teams" FOREIGN KEY ("goalie_team_id")
	REFERENCES "nhl"."teams"("team_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."shootout_attempts" ADD CONSTRAINT "shootout_attempt_goalies_to_players" FOREIGN KEY ("goalie_id")
	REFERENCES "nhl"."players"("player_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."shot_attempts" ADD CONSTRAINT "shot_attempts_to_games" FOREIGN KEY ("game_id")
	REFERENCES "nhl"."games"("game_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;

ALTER TABLE "nhl"."shot_attempts" ADD CONSTRAINT "shot_attempts_to_teams" FOREIGN KEY ("team_id")
	REFERENCES "nhl"."teams"("team_id")
	MATCH SIMPLE
	ON DELETE CASCADE
	ON UPDATE CASCADE
	NOT DEFERRABLE;


