-- 在 V009 后执行。任务保存已在提交时通过权限校验的平台样例图片 ID。
ALTER TABLE agent_task
    ADD COLUMN examplePictureIdsJson varchar(1024) NULL AFTER inputMessageId;
