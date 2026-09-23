-- WhatsApp conversation history, one row per message.
create table if not exists conversation_messages (
    id bigint generated always as identity primary key,
    phone text not null,
    role text not null check (role in ('user', 'assistant')),
    content text not null,
    created_at timestamptz not null default now()
);

create index if not exists conversation_messages_phone_created_idx
    on conversation_messages (phone, created_at desc);

alter table conversation_messages enable row level security;
