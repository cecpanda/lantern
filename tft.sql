BEGIN;
--
-- Create model Audit
--
CREATE TABLE "tft_audit" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "p_time" datetime NULL, "recipe_close" varchar(10) NULL, "recipe_confirm" varchar(10) NULL, "c_time" datetime NULL, "rejected" bool NOT NULL, "reason" text NULL, "created" datetime NOT NULL, "c_signer_id" integer NULL REFERENCES "account_user" ("id") DEFERRABLE INITIALLY DEFERRED);
--
-- Create model ID
--
CREATE TABLE "tft_id" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "created" datetime NOT NULL);
--
-- Create model Lot
--
CREATE TABLE "tft_lot" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(14) NULL, "created" datetime NOT NULL);
--
-- Create model LotInfo
--
CREATE TABLE "tft_lotinfo" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "kind" varchar(4) NOT NULL, "size" varchar(10) NULL, "height" varchar(10) NULL);
--
-- Create model Mark
--
CREATE TABLE "tft_mark" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "mark" integer NOT NULL, "group_id" integer NOT NULL UNIQUE REFERENCES "auth_group" ("id") DEFERRABLE INITIALLY DEFERRED);
--
-- Create model Order
--
CREATE TABLE "tft_order" ("id" varchar(20) NOT NULL PRIMARY KEY, "status" varchar(2) NOT NULL, "next" varchar(2) NULL, "created" datetime NOT NULL, "modified" datetime NOT NULL, "found_step" varchar(30) NOT NULL, "found_time" datetime NOT NULL, "eq" varchar(50) NOT NULL, "kind" varchar(30) NOT NULL, "step" varchar(50) NOT NULL, "reason" text NOT NULL, "users" varchar(10) NOT NULL, "charge_users" varchar(10) NOT NULL, "desc" text NOT NULL, "start_time" datetime NULL, "end_time" datetime NULL, "lot_num" varchar(10) NULL, "lots" text NULL, "condition" text NOT NULL, "defect_type" bool NULL, "charge_group_id" integer NOT NULL REFERENCES "auth_group" ("id") DEFERRABLE INITIALLY DEFERRED, "group_id" integer NOT NULL REFERENCES "auth_group" ("id") DEFERRABLE INITIALLY DEFERRED, "mod_user_id" integer NULL REFERENCES "account_user" ("id") DEFERRABLE INITIALLY DEFERRED, "user_id" integer NOT NULL REFERENCES "account_user" ("id") DEFERRABLE INITIALLY DEFERRED);
--
-- Create model OrderFlow
--
CREATE TABLE "tft_orderflow" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "flow" integer NOT NULL, "created" datetime NOT NULL, "order_id" varchar(20) NOT NULL REFERENCES "tft_order" ("id") DEFERRABLE INITIALLY DEFERRED);
--
-- Create model RecoverAudit
--
CREATE TABLE "tft_recoveraudit" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "qc_time" datetime NULL, "p_time" datetime NULL, "rejected" bool NOT NULL, "reason" text NULL, "p_signer_id" integer NULL REFERENCES "account_user" ("id") DEFERRABLE INITIALLY DEFERRED, "qc_signer_id" integer NULL REFERENCES "account_user" ("id") DEFERRABLE INITIALLY DEFERRED);
--
-- Create model RecoverOrder
--
CREATE TABLE "tft_recoverorder" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "created" datetime NOT NULL, "modified" datetime NOT NULL, "solution" text NOT NULL, "explain" text NOT NULL, "partial" bool NOT NULL, "eq" varchar(50) NULL, "kind" varchar(30) NULL, "step" varchar(50) NULL, "mod_user_id" integer NULL REFERENCES "account_user" ("id") DEFERRABLE INITIALLY DEFERRED, "order_id" varchar(20) NOT NULL REFERENCES "tft_order" ("id") DEFERRABLE INITIALLY DEFERRED, "user_id" integer NOT NULL REFERENCES "account_user" ("id") DEFERRABLE INITIALLY DEFERRED);
--
-- Create model Remark
--
CREATE TABLE "tft_remark" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "content" text NOT NULL, "created" datetime NOT NULL, "order_id" varchar(20) NOT NULL REFERENCES "tft_order" ("id") DEFERRABLE INITIALLY DEFERRED, "user_id" integer NOT NULL REFERENCES "account_user" ("id") DEFERRABLE INITIALLY DEFERRED);
--
-- Create model Report
--
CREATE TABLE "tft_report" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "file" varchar(100) NOT NULL, "order_id" varchar(20) NOT NULL REFERENCES "tft_order" ("id") DEFERRABLE INITIALLY DEFERRED);
--
-- Create model Shortcut
--
CREATE TABLE "tft_shortcut" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "name" varchar(10) NOT NULL);
--
-- Create model ShortcutContent
--
CREATE TABLE "tft_shortcutcontent" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "content" varchar(50) NOT NULL, "name_id" integer NOT NULL REFERENCES "tft_shortcut" ("id") DEFERRABLE INITIALLY DEFERRED);
--
-- Add field recover_order to recoveraudit
--
ALTER TABLE "tft_recoveraudit" RENAME TO "tft_recoveraudit__old";
CREATE TABLE "tft_recoveraudit" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "qc_time" datetime NULL, "p_time" datetime NULL, "rejected" bool NOT NULL, "reason" text NULL, "p_signer_id" integer NULL REFERENCES "account_user" ("id") DEFERRABLE INITIALLY DEFERRED, "qc_signer_id" integer NULL REFERENCES "account_user" ("id") DEFERRABLE INITIALLY DEFERRED, "recover_order_id" integer NOT NULL UNIQUE REFERENCES "tft_recoverorder" ("id") DEFERRABLE INITIALLY DEFERRED);
INSERT INTO "tft_recoveraudit" ("id", "qc_time", "p_time", "rejected", "reason", "p_signer_id", "qc_signer_id", "recover_order_id") SELECT "id", "qc_time", "p_time", "rejected", "reason", "p_signer_id", "qc_signer_id", NULL FROM "tft_recoveraudit__old";
DROP TABLE "tft_recoveraudit__old";
CREATE INDEX "tft_audit_c_signer_id_411867d1" ON "tft_audit" ("c_signer_id");
CREATE INDEX "tft_order_charge_group_id_63975f91" ON "tft_order" ("charge_group_id");
CREATE INDEX "tft_order_group_id_62876dd8" ON "tft_order" ("group_id");
CREATE INDEX "tft_order_mod_user_id_2d40a6c9" ON "tft_order" ("mod_user_id");
CREATE INDEX "tft_order_user_id_3e1532b9" ON "tft_order" ("user_id");
CREATE INDEX "tft_orderflow_order_id_e1ee5db7" ON "tft_orderflow" ("order_id");
CREATE INDEX "tft_recoverorder_mod_user_id_97186877" ON "tft_recoverorder" ("mod_user_id");
CREATE INDEX "tft_recoverorder_order_id_13fe224b" ON "tft_recoverorder" ("order_id");
CREATE INDEX "tft_recoverorder_user_id_ebeca9ec" ON "tft_recoverorder" ("user_id");
CREATE INDEX "tft_remark_order_id_f7dfd5f1" ON "tft_remark" ("order_id");
CREATE INDEX "tft_remark_user_id_8b36dc16" ON "tft_remark" ("user_id");
CREATE INDEX "tft_report_order_id_fc7354f4" ON "tft_report" ("order_id");
CREATE INDEX "tft_shortcutcontent_name_id_757aa19c" ON "tft_shortcutcontent" ("name_id");
CREATE INDEX "tft_recoveraudit_p_signer_id_09a18152" ON "tft_recoveraudit" ("p_signer_id");
CREATE INDEX "tft_recoveraudit_qc_signer_id_298ef56c" ON "tft_recoveraudit" ("qc_signer_id");
--
-- Add field order to audit
--
ALTER TABLE "tft_audit" RENAME TO "tft_audit__old";
CREATE TABLE "tft_audit" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "p_time" datetime NULL, "recipe_close" varchar(10) NULL, "recipe_confirm" varchar(10) NULL, "c_time" datetime NULL, "rejected" bool NOT NULL, "reason" text NULL, "created" datetime NOT NULL, "c_signer_id" integer NULL REFERENCES "account_user" ("id") DEFERRABLE INITIALLY DEFERRED, "order_id" varchar(20) NOT NULL UNIQUE REFERENCES "tft_order" ("id") DEFERRABLE INITIALLY DEFERRED);
INSERT INTO "tft_audit" ("id", "p_time", "recipe_close", "recipe_confirm", "c_time", "rejected", "reason", "created", "c_signer_id", "order_id") SELECT "id", "p_time", "recipe_close", "recipe_confirm", "c_time", "rejected", "reason", "created", "c_signer_id", NULL FROM "tft_audit__old";
DROP TABLE "tft_audit__old";
CREATE INDEX "tft_audit_c_signer_id_411867d1" ON "tft_audit" ("c_signer_id");
--
-- Add field p_signer to audit
--
ALTER TABLE "tft_audit" RENAME TO "tft_audit__old";
CREATE TABLE "tft_audit" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "p_time" datetime NULL, "recipe_close" varchar(10) NULL, "recipe_confirm" varchar(10) NULL, "c_time" datetime NULL, "rejected" bool NOT NULL, "reason" text NULL, "created" datetime NOT NULL, "c_signer_id" integer NULL REFERENCES "account_user" ("id") DEFERRABLE INITIALLY DEFERRED, "order_id" varchar(20) NOT NULL UNIQUE REFERENCES "tft_order" ("id") DEFERRABLE INITIALLY DEFERRED, "p_signer_id" integer NULL REFERENCES "account_user" ("id") DEFERRABLE INITIALLY DEFERRED);
INSERT INTO "tft_audit" ("id", "p_time", "recipe_close", "recipe_confirm", "c_time", "rejected", "reason", "created", "c_signer_id", "order_id", "p_signer_id") SELECT "id", "p_time", "recipe_close", "recipe_confirm", "c_time", "rejected", "reason", "created", "c_signer_id", "order_id", NULL FROM "tft_audit__old";
DROP TABLE "tft_audit__old";
CREATE INDEX "tft_audit_c_signer_id_411867d1" ON "tft_audit" ("c_signer_id");
CREATE INDEX "tft_audit_p_signer_id_d5e9a68f" ON "tft_audit" ("p_signer_id");
COMMIT;
