import sqlite3

__connection = None

ex_default_categories = ['food', 'house', 'entertainment']
in_default_categories = ['salary', 'gift']

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
        c.execute('DROP TABLE IF EXISTS incomes_categories')
        c.execute('DROP TABLE IF EXISTS expenses_categories')
        c.execute('DROP TABLE IF EXISTS reminders')


    c.execute('''
        CREATE TABLE IF NOT EXISTS user (
        id INTEGER PRIMARY KEY, 
        user_id INTEGER NOT NULL UNIQUE,
        name TEXT
        );'''
    )

    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY UNIQUE, 
        user_id INTEGER NOT NULL,
        date DATE,
        sum INTEGER,
        type INTEGER
        );''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS incomes (
        id INTEGER PRIMARY KEY UNIQUE, 
        user_id INTEGER NOT NULL,
        date DATE,
        sum INTEGER,
        type INTEGER
        );''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS balance (
        id INTEGER PRIMARY KEY, 
        user_id INTEGER NOT NULL UNIQUE,
        total BIGINT
        );''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS incomes_categories (
        id INTEGER PRIMARY KEY, 
        user_id INTEGER,
        num INTEGER,
        name TEXT
        );''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses_categories (
        id INTEGER PRIMARY KEY, 
        user_id INTEGER,
        num INTEGER,
        name TEXT 
        );''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        name TEXT,
        date DATE
        );''')

    conn.commit()

def add_default_categories(conn, user_id: int):
    # conn = get_connection()
    c = conn.cursor()

    for i in range(len(in_default_categories)):
        c.execute('INSERT INTO incomes_categories (user_id, num, name) VALUES (?, ?, ?);',
                  (user_id,  i + 1, in_default_categories[i]))

    for i in range(len(ex_default_categories)):
        c.execute('INSERT INTO expenses_categories (user_id, num, name) VALUES (?, ?, ?);',
                  (user_id,  i + 1, ex_default_categories[i]))



@ensure_connection
def add_user(conn, user_id: int, name: str):
    # conn = get_connection()
    c = conn.cursor()
    c.execute('INSERT INTO user (user_id, name) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET name = name;',
              (user_id, name))
    c.execute('INSERT INTO balance (user_id, total) VALUES (?, ?);',
              (user_id, 0))
    add_default_categories(conn, user_id)
    conn.commit()


@ensure_connection
def add_money_transfer(conn, user_id: int, sum: int, type: int, date: str, ex_in: str):
    # conn = get_connection()
    c = conn.cursor()
    # пока один пользователь - добавляем его при start
    # c.execute('INSERT INTO user (user_id, name) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET name = name;', (user_id, name))
    if ex_in == 'ex':
        c.execute('INSERT INTO expenses (user_id, date, sum, type) VALUES (?, ?, ?, ?);', (user_id, date, sum, type))
        c.execute(f'UPDATE balance SET total = (SELECT total FROM balance WHERE user_id={user_id}) - {sum} WHERE user_id={user_id};')
        conn.commit()
    else:
        c.execute('INSERT INTO incomes (user_id, date, sum, type) VALUES (?, ?, ?, ?);', (user_id, date, sum, type))
        c.execute(
            f'UPDATE balance SET total = {sum} + (SELECT total FROM balance WHERE user_id={user_id}) WHERE user_id={user_id};')
        conn.commit()


@ensure_connection
def add_category(conn, user_id: int, type_name: str, ex_in: str):
    # conn = get_connection()
    c = conn.cursor()
    if ex_in == 'ex':
        c.execute(f'SELECT MAX(num) FROM expenses_categories WHERE user_id={user_id};')
        last_record = c.fetchall()[0][0]
        c.execute('INSERT INTO expenses_categories (user_id, num, name) VALUES (?, ?, ?);',
                  (user_id, last_record + 1, type_name))
    else:
        c.execute(f'SELECT MAX(num) FROM incomes_categories WHERE user_id={user_id};')
        last_record = c.fetchall()[0][0]
        c.execute('INSERT INTO incomes_categories (user_id, num, name) VALUES (?, ?, ?);',
                  (user_id, last_record + 1, type_name))
    conn.commit()


@ensure_connection
def get_balance(conn, user_id: int):
    # conn = get_connection()
    c = conn.cursor()
    c.execute(f'SELECT total FROM balance WHERE user_id={user_id};')
    res = c.fetchall()
    return res

@ensure_connection
def get_categories(conn, user_id: int, ex_in: str):
    # conn = get_connection()
    c = conn.cursor()
    if ex_in == 'ex':
        c.execute(f'SELECT num, name FROM expenses_categories WHERE user_id={user_id};')
        res1 = c.fetchall()
        c.execute(f'SELECT name, num FROM expenses_categories WHERE user_id={user_id};')
        res2 = c.fetchall()
        return (len(res1), dict(res1), dict(res2))
    else:
        c.execute(f'SELECT num, name FROM incomes_categories WHERE user_id={user_id};')
        res1 = c.fetchall()
        c.execute(f'SELECT name, num FROM incomes_categories WHERE user_id={user_id};')
        res2 = c.fetchall()
        return (len(res1), dict(res1), dict(res2))

@ensure_connection
def add_reminder(conn, user_id: int, name: str, date: str):
    # conn = get_connection()
    c = conn.cursor()
    c.execute('INSERT INTO reminders (user_id, name, date) VALUES (?, ?, ?);',
                  (user_id, name, date))
    conn.commit()

@ensure_connection
def sql_execute(conn, sql: str):
    # conn = get_connection()
    c = conn.cursor()
    c.execute(sql)
    res = c.fetchall()
    return res
