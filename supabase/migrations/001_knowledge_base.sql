create table if not exists knowledge_base (
    id text primary key,
    category text not null,
    subcategory text,
    title text not null,
    content text not null,
    sample_questions text[],
    keywords text[],
    location text,
    county text,
    plot_size text,
    property_type text,
    status text,
    price text,
    source_url text,
    needs_verification text,
    created_at timestamptz not null default now()
);

create index if not exists knowledge_base_category_idx on knowledge_base (category);
