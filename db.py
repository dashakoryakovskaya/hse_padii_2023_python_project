import sqlite3
import bot
import pandas as pd
from prettytable import from_db_cursor
from dateutil.relativedelta import relativedelta
import datetime
import random

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
def add_real_data(conn, user_id, name_of_file):
    # c = conn.cursor()
    df_flat = pd.read_csv(f"{name_of_file}.csv")
    filtered_data = df_flat[df_flat.iloc[:, 3] == "debit"]
    columns_to_drop = [1, 3, 4, 5]
    filtered_data = filtered_data.drop(filtered_data.columns[columns_to_drop], axis=1)
    filtered_data.columns = ['date', 'sum']
    filtered_data['date'] = pd.to_datetime(filtered_data['date'])

    for i, row in filtered_data.iterrows():
        filtered_data.loc[(filtered_data['date'] == row['date']), 'date'] = row['date'].replace(
            year=row['date'].year + 4)

    grouped_data = filtered_data.groupby('date')['sum'].sum().reset_index()
    grouped_data = grouped_data.set_index('date')
    df_resampled = grouped_data.resample('D').fillna(method='ffill')
    df_resampled = df_resampled.reset_index()

    c = conn.cursor()
    total_sum = df_resampled['sum'].sum()
    c.execute(f'UPDATE balance SET total = (SELECT total FROM balance WHERE user_id={user_id}) - {total_sum} WHERE user_id={user_id};')

    df_resampled["type"] = random.randint(1, 10)
    df_resampled.insert(loc=0, column='user_id', value=user_id)
    df = df_resampled
    df.index.rename('id', inplace=True)
    # df_resampled["user_id"] = user_id
    # print(df)
    df.to_sql('expenses', con=conn, schema='dbo', if_exists='replace')
    conn.commit()
    # c.execute(f'INSERT INTO expenses (user_id, date, sum, type) VALUES (?, ?, ?, ?);', (user_id, date, sum, type))


# @ensure_connection
# def add_real_data_2(conn, user_id):
#     # c = conn.cursor()
#     df_flat = pd.read_csv("personal_transactions_bot.csv")
#     filtered_data = df_flat[df_flat.iloc[:, 3] == "debit"]
#     columns_to_drop = [1, 3, 4, 5]
#     filtered_data = filtered_data.drop(filtered_data.columns[columns_to_drop], axis=1)
#     filtered_data.columns = ['date', 'sum']
#     filtered_data['date'] = pd.to_datetime(filtered_data['date'])
#     for i, row in filtered_data.iterrows():
#         filtered_data.loc[(filtered_data['date'] ==  row['date']), 'date'] = row['date'].
#         replace(year=row['date'].year + 4)
#     grouped_data = filtered_data.groupby('date')['sum'].sum().reset_index()
#     grouped_data = grouped_data.set_index('date')
#     df_resampled = grouped_data.resample('D').fillna(method='ffill')
#     df_resampled = df_resampled.reset_index()
#     df_resampled["type"] = 1
#     df_resampled.insert(loc=0, column='user_id', value=user_id)
#     df = df_resampled
#     df.index.rename('id', inplace=True)
#     # df_resampled["user_id"] = user_id
#     print(df)
#     df.to_sql('expenses', con=conn, schema='dbo', if_exists='replace')


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
        c.execute('DROP TABLE IF EXISTS cards')
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
        date INT,
        time TIME,
        category INT
        );''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS reminders_text (
        id INTEGER PRIMARY KEY,
        text TINYTEXT
        );''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS cards (
    id INTEGER PRIMARY KEY, 
    user_id INTEGER,
    name TEXT,
    card BLOB NOT NULL
    );''')

    conn.commit()
    add_real_data(user_id=219102395, name_of_file='personal_transactions_bot')
    add_real_data(user_id=1067952257, name_of_file='personal_transactions_bot')


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
    c.execute(f'SELECT MAX(num) FROM {ex_in} categories WHERE user_id={user_id};')
    last_record = c.fetchall()[0][0]
    c.execute(f'INSERT INTO {ex_in} categories (user_id, num, name) VALUES (?, ?, ?);',
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


def get_categories(ex_in: str):
    if ex_in == 'ex':
        return ex_default_categories
    else:
        return in_default_categories


def get_categories_rev(ex_in: str):
    if ex_in == 'ex':
        return ex_default_categories_rev
    else:
        return in_default_categories_rev


@ensure_connection
def get_sum_group(conn, user_id: int, ex_in: str, all_period=True, data_start='', data_end=''):
    c = conn.cursor()
    if ex_in == 'ex':
        ex_in = "expenses"
    else:
        ex_in = "incomes"
    sql = f'SELECT type, SUM(sum) FROM {ex_in} WHERE user_id={user_id} GROUP BY type' if all_period else \
            f'SELECT type, SUM(sum) FROM {ex_in} WHERE user_id={user_id} AND date BETWEEN \'{data_start}\' AND \'{data_end}\' GROUP BY type'

    c.execute(sql)
    res = c.fetchall()
    y = []
    lables = []
    categories = get_categories_rev(ex_in=ex_in[:2])
    for i in range(len(res)):
        lables.append(categories[res[i][0]])
        y.append(res[i][1])

    return [y, lables]


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


@ensure_connection
def get_all_user_ids(conn):
    c = conn.cursor()
    c.execute('SELECT user_id FROM user')
    res = c.fetchall()
    return res


@ensure_connection
def get_all_reminders(conn, user_id: int):
    c = conn.cursor()
    c.execute(f'SELECT id, type, date, time, category FROM reminders WHERE user_id={user_id};')
    res = c.fetchall()
    # print(res)
    return res


@ensure_connection
def add_reminder(conn, user_id: int, time='', category=-1, date=-1, text="Мечтаю узнать о том, сколько ты сегодня"
                                                                         " потратил! Ну и получил🤑", type=0):
    # conn = get_connection()
    c = conn.cursor()
    c.execute('INSERT INTO reminders (user_id, type, date, time, category) VALUES (?, ?, ?, ?, ?);',
              (user_id, type, date, time, category))
    c.execute('INSERT INTO reminders_text (text) VALUES (?);', [text])
    if type == 0:
        c.execute(f'SELECT id FROM reminders WHERE user_id={user_id} AND type={type} AND time=\'{time}\';')
    else:
        c.execute(f'SELECT id FROM reminders WHERE user_id={user_id} AND type={type} AND date={date} AND time=\'{time}\';')
    notification_id = c.fetchall()[0][0]
    # print(notification_id)
    bot.create_notification(notification_id, type, user_id, text, date, time, category)

    conn.commit()


@ensure_connection
def erase_reminder(conn, notification_id: int):
    c = conn.cursor()
    c.execute(f'DELETE FROM reminders WHERE id={notification_id};')
    c.execute(f'DELETE FROM reminders_text WHERE id={notification_id};')
    bot.cancel_notification(notification_id)

    conn.commit()


@ensure_connection
def add_card(conn, user_id: int, name: str, card):
    # conn = get_connection()
    c = conn.cursor()
    c.execute('INSERT INTO cards (user_id, name, card) VALUES (?, ?, ?);',
              (user_id, name, card))
    conn.commit()


@ensure_connection
def erase_card(conn, user_id: int, name: str):
    c = conn.cursor()
    c.execute(f'DELETE FROM cards WHERE user_id={user_id} AND name="{name}";')
    conn.commit()


@ensure_connection
def get_all_cards_name(conn, user_id: int):
    c = conn.cursor()
    c.execute(f'SELECT name FROM cards WHERE user_id={user_id};')
    res = c.fetchall()
    return res


@ensure_connection
def get_cards(conn, user_id: int):
    # conn = get_connection()
    c = conn.cursor()
    c.execute(f'SELECT name, card FROM cards WHERE user_id={user_id};')
    res = c.fetchall()
    return res


@ensure_connection
def get_df(conn, user_id: int):
    c = conn.cursor()
    query = f'SELECT date, sum FROM expenses WHERE user_id={user_id};'
    df = pd.read_sql_query(query, conn)
    return df

@ensure_connection
def sql_execute(conn, sql):
    # conn = get_connection()
    c = conn.cursor()
    c.execute(sql)
    res = c.fetchall()
    return res
