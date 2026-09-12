ALTER TABLE agent_conversation
    ADD COLUMN allSpaces TINYINT NOT NULL DEFAULT 0 COMMENT 'Explicit all-authorized-scope conversation',
    ADD COLUMN scopeSpaceIdsJson TEXT NULL COMMENT 'Creation-time scope snapshot; reauthorized on every access';
