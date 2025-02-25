CREATE TABLE IF NOT EXISTS "USER" (
    user_id BIGSERIAL PRIMARY KEY,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "USER_Profile" (
    user_id BIGINT PRIMARY KEY,
    f_name VARCHAR(255),
    l_name VARCHAR(255),
    age INT,
    sex VARCHAR(50),
    job VARCHAR(255),
    city VARCHAR(255),
    goal TEXT,
    solution TEXT,
    CONSTRAINT fk_user_profile_user FOREIGN KEY (user_id) REFERENCES "USER"(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS "USER_Feedback" (
    user_id BIGINT PRIMARY KEY,
    interaction_rating INT,
    useful_functions TEXT,
    missing_features TEXT,
    interface_convenience TEXT,
    technical_improvements TEXT,
    CONSTRAINT fk_user_feedback_user FOREIGN KEY (user_id) REFERENCES "USER"(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS "Conversation" (
    dialogue_id BIGSERIAL PRIMARY KEY,
    short_summary TEXT,
    summary TEXT
);

CREATE TABLE IF NOT EXISTS "Message" (
    msg_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    dialogue_id BIGINT NOT NULL,
    role VARCHAR(50),
    response TEXT,
    response_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    emotion TEXT,
    CONSTRAINT fk_message_user FOREIGN KEY (user_id) REFERENCES "USER"(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_message_conversation FOREIGN KEY (dialogue_id) REFERENCES "Conversation"(dialogue_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS "Train_Data" (
    train_id BIGSERIAL PRIMARY KEY,
    dialogue_id BIGINT NOT NULL,
    user_response TEXT,
    aivy_response TEXT,
    CONSTRAINT fk_train_data_conversation FOREIGN KEY (dialogue_id) REFERENCES "Conversation"(dialogue_id) ON DELETE CASCADE
);
