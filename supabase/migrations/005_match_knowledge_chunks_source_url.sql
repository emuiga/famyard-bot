-- Return each entry's source_url so replies can include property links.
-- The return type changes, so the function must be dropped and recreated.
drop function if exists match_knowledge_chunks(extensions.vector, int, float);

create function match_knowledge_chunks(
    query_embedding extensions.vector(1536),
    match_count int default 5,
    match_threshold float default 0.6
)
returns table (
    kb_id text,
    category text,
    title text,
    content text,
    source_url text,
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
        kb.source_url,
        kb.needs_verification,
        1 - (c.embedding <=> query_embedding) as similarity
    from knowledge_chunks c
    join knowledge_base kb on kb.id = c.kb_id
    where 1 - (c.embedding <=> query_embedding) > match_threshold
    order by c.embedding <=> query_embedding
    limit match_count;
$$;
