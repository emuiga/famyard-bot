-- WhatsApp message ids already handled, so Meta's duplicate deliveries are ignored.
create table if not exists processed_messages (
    message_id text primary key,
    created_at timestamptz not null default now()
);

alter table processed_messages enable row level security;
