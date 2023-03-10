import sqlite3
import bot
from prettytable import from_db_cursor

__connection = None

ex_default_categories = {'Развлечения': 1, 'Автомобиль': 2, 'Дом': 3, 'Здоровье': 4, 'Одежда': 5, 'Питание': 6,
                         'Подарки': 7, 'Семейные расходы': 8, 'Услуги': 9, 'Другое': 10}
ex_default_categories_rev = {1: 'Развлечения', 2: 'Автомобиль', 3: 'Дом', 4: 'Здоровье', 5: 'Одежда', 6: 'Питание',
                             7: 'Подарки', 8: 'Семейные расходы', 9: 'Услуги', 10: 'Другое'}
in_default_categories = {'Зарплата': 1, 'Подарок': 2, 'Инвестиции': 3, 'Другое': 4}
in_default_categories_rev = {1: 'Зарплата', 2: 'Подарок', 3: 'Инвестиции', 4: 'Другое'}

kinds_of_notification = {0: "Ежедневные", 1: "По дате"}


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
        # c.execute('DROP TABLE IF EXISTS incomes_categories')
        # c.execute('DROP TABLE IF EXISTS expenses_categories')
        c.execute('DROP TABLE IF EXISTS reminders')
        c.execute('DROP TABLE IF EXISTS reminders_text')

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
        user_id INTEGER NOT NULL,
        total BIGINT
        );''')

    # c.execute('''
    #     CREATE TABLE IF NOT EXISTS incomes_categories (
    #     id INTEGER PRIMARY KEY,
    #     user_id INTEGER,
    #     num INTEGER,
    #     name TEXT
    #     );''')
    #
    # c.execute('''
    #     CREATE TABLE IF NOT EXISTS expenses_categories (
    #     id INTEGER PRIMARY KEY,
    #     user_id INTEGER,
    #     num INTEGER,
    #     name TEXT
    #     );''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        type INTEGER,
        date DATE,
        time TIME
        );''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS reminders_text (
        id INTEGER PRIMARY KEY,
        text TINYTEXT
        );''')

    conn.commit()


def add_default_categories(conn, user_id: int):
    # conn = get_connection()
    c = conn.cursor()

    for i in range(len(in_default_categories)):
        c.execute('INSERT INTO incomes_categories (user_id, num, name) VALUES (?, ?, ?);',
                  (user_id, i + 1, in_default_categories[i]))

    for i in range(len(ex_default_categories)):
        c.execute('INSERT INTO expenses_categories (user_id, num, name) VALUES (?, ?, ?);',
                  (user_id, i + 1, ex_default_categories[i]))


@ensure_connection
def add_user(conn, user_id: int, name: str):
    # conn = get_connection()
    c = conn.cursor()
    c.execute('INSERT INTO user (user_id, name) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET name = name;',
              (user_id, name))
    c.execute('INSERT INTO balance (user_id, total) VALUES (?, ?);',
              (user_id, 0))
    # add_default_categories(conn, user_id)
    conn.commit()


@ensure_connection
def add_money_transfer(conn, user_id: int, sum: int, type: int, date: str, ex_in: str):
    # conn = get_connection()
    c = conn.cursor()
    # пока один пользователь - добавляем его при start
    # c.execute('INSERT INTO user (user_id, name) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET name = name;', (user_id, name))
    if ex_in == 'ex':
        ex_in = "expenses"
        c.execute(
            f'UPDATE balance SET total = (SELECT total FROM balance WHERE user_id={user_id}) - {sum} WHERE user_id={user_id};')
    else:
        ex_in = "incomes"
        c.execute(
            f'UPDATE balance SET total = (SELECT total FROM balance WHERE user_id={user_id}) + {sum} WHERE user_id={user_id};')

    c.execute(f'INSERT INTO {ex_in} (user_id, date, sum, type) VALUES (?, ?, ?, ?);', (user_id, date, sum, type))
    conn.commit()


@ensure_connection
def add_category(conn, user_id: int, type_name: str, ex_in: str):
    # conn = get_connection()
    c = conn.cursor()
    if ex_in == 'ex':
        ex_in = "expenses"
    else:
        ex_in = "incomes"
    c.execute(f'SELECT MAX(num) FROM {ex_in}_categories WHERE user_id={user_id};')
    last_record = c.fetchall()[0][0]
    c.execute(f'INSERT INTO {ex_in}_categories (user_id, num, name) VALUES (?, ?, ?);',
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
def get_sum(conn, user_id: int, type: int, ex_in: str, all_period=False, data_start='', data_end=''):
    # conn = get_connection()
    if ex_in == 'ex':
        ex_in = "expenses"
    else:
        ex_in = "incomes"
    if type == -1:
        sql = f'SELECT SUM(sum) FROM {ex_in} WHERE user_id={user_id}' if all_period else \
            f'SELECT SUM(sum) FROM {ex_in} WHERE user_id={user_id} AND date BETWEEN \'{data_start}\' AND \'{data_end}\''
    else:
        sql = f'SELECT SUM(sum) FROM {ex_in} WHERE user_id={user_id} AND type={type}' if all_period else \
            f'SELECT SUM(sum) FROM {ex_in} WHERE user_id={user_id} AND type={type} AND date BETWEEN \'{data_start}\' AND \'{data_end}\''

    c = conn.cursor()
    c.execute(sql)
    res = c.fetchall()[0][0]
    return 0 if res is None else res
'''if (ex_in == 'ex'):
        if all_period:
            c.execute(f'SELECT SUM(sum) FROM expenses WHERE user_id={user_id} AND type={type};')
            res = c.fetchall()[0][0]
            return res
        else:
            c.execute(
                f'SELECT SUM(sum) FROM expenses WHERE user_id={user_id} AND type={type} AND date BETWEEN {data_start} AND {data_end};')
            res = c.fetchall()[0][0]
            return res
    else:
        if all_period:
            c.execute(f'SELECT SUM(sum) FROM incomes WHERE user_id={user_id} AND type={type};')
            res = c.fetchall()[0][0]
            return res
        else:
            c.execute(
                f'SELECT SUM(sum) FROM incomes WHERE user_id={user_id} AND type={type} AND date BETWEEN {data_start} AND {data_end};')
            res = c.fetchall()[0][0]
            return res '''


@ensure_connection
def get_all_statistic(conn, user_id: int, type: int, ex_in: str, all_period=False, data_start='', data_end=''):
    # conn = get_connection()
    c = conn.cursor()
    if ex_in == 'ex':
        ex_in = "expenses"
    else:
        ex_in = "incomes"
    if type == -1:
        sql = f'SELECT sum, date, type FROM {ex_in} WHERE user_id={user_id}' if all_period else \
            f'SELECT sum, date, type FROM {ex_in} WHERE user_id={user_id} AND date BETWEEN \'{data_start}\' AND \'{data_end}\''
    else:
        sql = f'SELECT sum, date, type FROM {ex_in} WHERE user_id={user_id} AND type={type};' if all_period else \
            f'SELECT sum, date, type FROM {ex_in} WHERE user_id={user_id} AND type={type} AND date BETWEEN \'{data_start}\' AND \'{data_end}\''


    c.execute(sql)
    table = from_db_cursor(c)
    table.field_names = ['Сумма', 'Дата', 'Категория']
    if ex_in == 'expenses':
        for i, _ in enumerate(table.rows):
            table.rows[i][2] = ex_default_categories_rev[table.rows[i][2]]
    else:
        for i, _ in enumerate(table.rows):
            table.rows[i][2] = in_default_categories_rev[table.rows[i][2]]
    return table

'''if (ex_in == 'ex'):
        if type == -1:
            if all_period:
                c.execute(f'SELECT sum, date, type FROM expenses WHERE user_id={user_id};')
            else:
                c.execute(
                    f'SELECT sum, date, type FROM expenses WHERE user_id={user_id} AND date BETWEEN {data_start} AND {data_end};')
        else:
            if all_period:
                c.execute(f'SELECT sum, date, type FROM expenses WHERE user_id={user_id} AND type={type};')
            else:
                c.execute(
                    f'SELECT sum, date, type FROM expenses WHERE user_id={user_id} AND type={type} AND date BETWEEN {data_start} AND {data_end};')
        table = from_db_cursor(c)
        table.field_names = ['Сумма', 'Дата', 'Категория']
        for i, _ in enumerate(table.rows):
            table.rows[i][2] = ex_default_categories_rev[table.rows[i][2]]
        return table
    else:
        if type == -1:
            if all_period:
                c.execute(f'SELECT sum, date, type FROM incomes WHERE user_id={user_id};')
            else:
                c.execute(
                    f'SELECT sum, date, type FROM incomes WHERE user_id={user_id} AND date BETWEEN {data_start} AND {data_end};')
        else:
            if all_period:
                c.execute(f'SELECT sum, date, type FROM incomes WHERE user_id={user_id} AND type={type};')
            else:
                c.execute(
                    f'SELECT sum, date, type FROM incomes WHERE user_id={user_id} AND type={type} AND date BETWEEN {data_start} AND {data_end};')
        table = from_db_cursor(c)
        table.field_names = ['Сумма', 'Дата', 'Категория']
        for i, _ in enumerate(table.rows):
            table.rows[i][2] = in_default_categories_rev[table.rows[i][2]]
        return table '''


'''@ensure_connection
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
        return (len(res1), dict(res1), dict(res2))'''


def get_categories(ex_in: str):
    if ex_in == 'ex':
        return ex_default_categories
    else:
        return in_default_categories


@ensure_connection
def get_all_user_ids(conn):
    c = conn.cursor()
    c.execute('SELECT user_id FROM user')
    res = c.fetchall()
    return res


@ensure_connection
def get_all_reminders(conn, user_id: int):
    c = conn.cursor()
    c.execute(f'SELECT id, type, date, time FROM reminders WHERE user_id={user_id};')
    res = c.fetchall()
    # print(res)
    return res


@ensure_connection
def add_reminder(conn, user_id: int, date='', time = '', text="Мечтаю узнать о том, сколько ты сегодня потратил! Ну и получил🤑", type=0):
    # conn = get_connection()
    c = conn.cursor()
    c.execute('INSERT INTO reminders (user_id, type, date, time) VALUES (?, ?, ?, ?);',
              (user_id, type, date, time))
    c.execute('INSERT INTO reminders_text (text) VALUES (?);', [text])
    if type == 0:
        c.execute(f'SELECT id FROM reminders WHERE user_id={user_id} AND type={type} AND time=\'{time}\';')
    else:
        c.execute(f'SELECT id FROM reminders WHERE user_id={user_id} AND type={type} AND date=\'{date}\' AND time=\'{time}\';')
    notification_id = c.fetchall()[0][0]
    # print(notification_id)
    bot.create_notification(notification_id, type, user_id, text, date, time)

    conn.commit()


@ensure_connection
def erase_reminder(conn, notification_id: int):
    c = conn.cursor()
    c.execute(f'DELETE FROM reminders WHERE id={notification_id};')
    c.execute(f'DELETE FROM reminders_text WHERE id={notification_id};')
    bot.cancel_notification(notification_id)

    conn.commit()


@ensure_connection
def sql_execute(conn, sql):
    # conn = get_connection()
    c = conn.cursor()
    c.execute(sql)
    res = c.fetchall()
    return res
