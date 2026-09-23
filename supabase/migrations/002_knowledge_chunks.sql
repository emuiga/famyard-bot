create extension if not exists vector with schema extensions;

-- One row per embedded piece of a knowledge_base entry.
-- Short entries produce a single chunk; long documents are split.
create table if not exists knowledge_chunks (
    id bigint generated always as identity primary key,
    kb_id text not null references knowledge_base (id) on delete cascade,
    chunk_index int not null,
    content text not null,
    token_count int not null,
    -- Must match EMBEDDING_DIMENSIONS (text-embedding-3-small = 1536)
    embedding extensions.vector(1536) not null,
    created_at timestamptz not null default now(),
    unique (kb_id, chunk_index)
);

create index if not exists knowledge_chunks_embedding_idx
    on knowledge_chunks using hnsw (embedding extensions.vector_cosine_ops);

alter table knowledge_chunks enable row level security;

create or replace function match_knowledge_chunks(
    query_embedding extensions.vector(1536),
    match_count int default 5,
    match_threshold float default 0.3
)
returns table (
    kb_id text,
    category text,
    title text,
    content text,
    needs_verification text,
    similarity float
)
language sql stable
set search_path = public, extensions
as $$
    select
        c.kb_id,
        kb.category,
        kb.title,
        c.content,
        kb.needs_verification,
        1 - (c.embedding <=> query_embedding) as similarity
    from knowledge_chunks c
    join knowledge_base kb on kb.id = c.kb_id
    where 1 - (c.embedding <=> query_embedding) > match_threshold
    order by c.embedding <=> query_embedding
    limit match_count;
$$;
