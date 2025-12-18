-- tasksテーブル作成
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    source_channel_id TEXT NOT NULL,
    source_message_ts TEXT NOT NULL,
    source_permalink TEXT NOT NULL,
    task_channel_id TEXT NOT NULL,
    task_message_ts TEXT,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'done', 'closed')),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    assignee_user_id TEXT,
    due_date DATE,
    next_remind_at TIMESTAMP WITH TIME ZONE,
    remind_kind TEXT CHECK (remind_kind IN ('due_minus_1', 'weekly')),
    escalate_at TIMESTAMP WITH TIME ZONE,
    reactors JSONB,
    CONSTRAINT uq_source UNIQUE (source_channel_id, source_message_ts)
);

-- インデックス作成
CREATE INDEX IF NOT EXISTS idx_tasks_source_channel_id ON tasks(source_channel_id);
CREATE INDEX IF NOT EXISTS idx_tasks_source_message_ts ON tasks(source_message_ts);
CREATE INDEX IF NOT EXISTS idx_tasks_task_message_ts ON tasks(task_message_ts);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_tasks_next_remind_at ON tasks(next_remind_at);
CREATE INDEX IF NOT EXISTS idx_tasks_escalate_at ON tasks(escalate_at);
