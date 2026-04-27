-- General legal chat sessions and messages (POST /api/chat, Clerk user–scoped)

CREATE TABLE IF NOT EXISTS legal_chats (
    id UUID PRIMARY KEY,
    clerk_user_id VARCHAR(255) NOT NULL REFERENCES users(clerk_user_id) ON DELETE CASCADE,
    title VARCHAR(512) NOT NULL DEFAULT 'New chat',
    language VARCHAR(16) NOT NULL DEFAULT 'en',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS legal_chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chat_id UUID NOT NULL REFERENCES legal_chats(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    language_code VARCHAR(16) NOT NULL DEFAULT 'en',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    CONSTRAINT legal_chat_messages_role_check CHECK (role IN ('user', 'assistant'))
);

CREATE INDEX IF NOT EXISTS idx_legal_chats_user_updated ON legal_chats(clerk_user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_legal_chat_messages_chat_created ON legal_chat_messages(chat_id, created_at);
