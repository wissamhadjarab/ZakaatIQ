def init_tables(db):
    cur = db.cursor()

    # USERS
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # FINANCIAL HISTORY
    cur.execute("""
        CREATE TABLE IF NOT EXISTS financial_history (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            income BYTEA,
            savings BYTEA,
            debts BYTEA,
            gold BYTEA,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ZAKAT RESULTS (ML)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS zakat_results (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            result TEXT,
            explanation TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # DONATIONS
    cur.execute("""
        CREATE TABLE IF NOT EXISTS donations (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            charity_name TEXT,
            amount NUMERIC,
            reference TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ZAKAT SNAPSHOTS (Deterministic Engine)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS zakat_snapshots (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,

        assets_total BYTEA NOT NULL,
        debts_total BYTEA NOT NULL,
        net_zakatable BYTEA NOT NULL,
        nisab BYTEA NOT NULL,
        zakat_due BYTEA NOT NULL,

        nisab_basis TEXT NOT NULL,
        zakat_rate NUMERIC NOT NULL,

        zakat_due_date DATE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
    # CHARITIES
    cur.execute("""
    CREATE TABLE IF NOT EXISTS charities (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    website TEXT,
    approved BOOLEAN DEFAULT FALSE
)
""")
    db.commit()