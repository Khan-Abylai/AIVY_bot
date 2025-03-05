-- Создание таблицы USER
CREATE TABLE IF NOT EXISTS "USER" (
    user_id BIGSERIAL PRIMARY KEY,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание таблицы USER_Profile
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
    CONSTRAINT fk_user_profile_user FOREIGN KEY (user_id)
        REFERENCES "USER"(user_id) ON DELETE CASCADE
);

-- Создание таблицы USER_Feedback
CREATE TABLE IF NOT EXISTS "USER_Feedback" (
    user_id BIGINT PRIMARY KEY,
    interaction_rating INT,
    useful_functions TEXT,
    missing_features TEXT,
    interface_convenience TEXT,
    technical_improvements TEXT,
    CONSTRAINT fk_user_feedback_user FOREIGN KEY (user_id)
        REFERENCES "USER"(user_id) ON DELETE CASCADE
);

-- Создание таблицы Conversation (удалён столбец short_summary)
CREATE TABLE IF NOT EXISTS "Conversation" (
    dialogue_id BIGSERIAL PRIMARY KEY,
    summary TEXT
);

-- Создание таблицы Message
CREATE TABLE IF NOT EXISTS "Message" (
    msg_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    dialogue_id BIGINT NOT NULL,
    role VARCHAR(50),
    response TEXT,
    response_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    emotion TEXT,
    CONSTRAINT fk_message_user FOREIGN KEY (user_id)
        REFERENCES "USER"(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_message_conversation FOREIGN KEY (dialogue_id)
        REFERENCES "Conversation"(dialogue_id) ON DELETE CASCADE
);

-- Создание таблицы Train_Data
CREATE TABLE IF NOT EXISTS "Train_Data" (
    train_id BIGSERIAL PRIMARY KEY,
    dialogue_id BIGINT NOT NULL,
    user_response TEXT,
    aivy_response TEXT,
    CONSTRAINT fk_train_data_conversation FOREIGN KEY (dialogue_id)
        REFERENCES "Conversation"(dialogue_id) ON DELETE CASCADE
);

-----------------------------------------------------
-- Вставка тестовых данных

-- Вставка тестовых пользователей
INSERT INTO "USER" (user_id, registration_date)
VALUES
    (1001, CURRENT_TIMESTAMP),
    (1002, CURRENT_TIMESTAMP),
    (1003, CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;

-- Вставка тестовых профилей
INSERT INTO "USER_Profile" (user_id, f_name, l_name, age, sex, job, city, goal, solution)
VALUES
    (1001, 'Ivan', 'Ivanov', 30, 'male', 'Engineer', 'Moscow', 'Выучить английский', 'Заниматься каждый день'),
    (1002, 'Maria', 'Petrova', 25, 'female', 'Designer', 'Saint Petersburg', 'Сменить работу', 'Прокачать портфолио'),
    (1003, 'John', 'Smith', 40, 'male', 'Teacher', 'New York', 'Углубить знания в AI', 'Пройти онлайн-курсы')
ON CONFLICT (user_id) DO NOTHING;

-- Вставка тестовой обратной связи
INSERT INTO "USER_Feedback" (user_id, interaction_rating, useful_functions, missing_features, interface_convenience, technical_improvements)
VALUES
    (1001, 5, 'Voice commands', 'Translation feature', 'Все ок', 'Больше примеров'),
    (1002, 3, 'Сохранение заметок', 'Голосовой ввод', 'Сложная навигация', 'Оптимизировать работу с БД'),
    (1003, 4, 'Список предыдущих сессий', 'Больше аналитики', 'В целом удобно', 'Нужен режим оффлайн')
ON CONFLICT (user_id) DO NOTHING;

-- Вставка тестовых диалогов (Conversation)
INSERT INTO "Conversation" (dialogue_id, summary)
VALUES
    (1, 'Подробное описание диалога'),
    (2, 'Более развернутое описание второй беседы')
ON CONFLICT DO NOTHING;

-- Вставка тестовых сообщений (Message)
INSERT INTO "Message" (user_id, dialogue_id, role, response, emotion)
VALUES
    (1001, 1, 'user', 'Привет, бот!', 'neutral'),
    (1001, 1, 'assistant', 'Здравствуйте! Чем могу помочь?', 'positive'),
    (1002, 2, 'user', 'Подскажи, как пройти в библиотеку?', 'confused'),
    (1002, 2, 'assistant', 'Библиотека за углом налево!', 'neutral')
ON CONFLICT DO NOTHING;

-- Вставка тестовых данных для Train_Data (для дообучения)
INSERT INTO "Train_Data" (dialogue_id, user_response, aivy_response)
VALUES
    (1, 'Привет, бот!', 'Здравствуйте! Чем могу помочь?'),
    (2, 'Подскажи, как пройти в библиотеку?', 'Библиотека за углом налево!')
ON CONFLICT DO NOTHING;
