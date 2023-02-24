import sqlite3

__connection = None


def ensure_connection(func):
    def inner(*args, **kwargs):
        with sqlite3.connect('user.db') as conn:
            res = func(*args, conn=conn, **kwargs)
        return res

    return inner


"""def get_connection():
    global __connection
    if __connection is None:
        __connection = sqlite3.connect('user.db')
    return __connection """


@ensure_connection
def init_db(conn, flag_drop: bool = False):
    # conn = get_connection()
    c = conn.cursor()

    if flag_drop:
        c.execute('DROP TABLE IF EXISTS user')
        c.execute('DROP TABLE IF EXISTS expenses')
        c.execute('DROP TABLE IF EXISTS incomes')
        c.execute('DROP TABLE IF EXISTS balance')

    c.execute('''
    CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY, 
    user_id INTEGER NOT NULL UNIQUE,
    name TEXT
    );''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY UNIQUE, 
        user_id INTEGER NOT NULL,
        date DATE,
        sum INTEGER,
        type TEXT
        );''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS incomes (
        id INTEGER PRIMARY KEY UNIQUE, 
        user_id INTEGER NOT NULL,
        date DATE,
        sum INTEGER,
        type TEXT
        );''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS balance (
        id INTEGER PRIMARY KEY, 
        user_id INTEGER NOT NULL,
        total BIGINT
        );''')

    conn.commit()


@ensure_connection
def add_user(conn, user_id: int, name: str):
    # conn = get_connection()
    c = conn.cursor()
    c.execute('INSERT INTO user (user_id, name) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET name = name;',
              (user_id, name))
    c.execute('INSERT INTO balance (user_id, total) VALUES (?, ?);',
              (user_id, 0))
    conn.commit()


@ensure_connection
def add_expenses(conn, user_id: int, name: str, sum: int, type: str, date: str):
    # conn = get_connection()
    c = conn.cursor()
    # пока один пользователь - добавляем его при start
    # c.execute('INSERT INTO user (user_id, name) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET name = name;', (user_id, name))
    c.execute('INSERT INTO expenses (user_id, date, sum, type) VALUES (?, ?, ?, ?);', (user_id, date, sum, type))
    c.execute(f'UPDATE balance SET total = (SELECT total FROM balance WHERE user_id={user_id}) - {sum} WHERE user_id={user_id};')
    conn.commit()


@ensure_connection
def add_incomes(conn, user_id: int, name: str, sum: int, type: str, date: str):
    # conn = get_connection()
    c = conn.cursor()
    # пока один пользователь - добавляем его при start
    # c.execute('INSERT INTO user (user_id, name) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET name = name;', (user_id, name))
    c.execute('INSERT INTO incomes (user_id, date, sum, type) VALUES (?, ?, ?, ?);', (user_id, date, sum, type))
    c.execute(f'UPDATE balance SET total = {sum} + (SELECT total FROM balance WHERE user_id={user_id}) WHERE user_id={user_id};')
    conn.commit()


@ensure_connection
def sql_execute(conn, sql):
    # conn = get_connection()
    c = conn.cursor()
    c.execute(sql)
    res = c.fetchall()
    return res
