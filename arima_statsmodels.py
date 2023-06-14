import sqlite3
import random
import datetime
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import statsmodels
from statsmodels.graphics.tsaplots import plot_predict
from statsmodels.tsa.arima_process import arma_generate_sample
from statsmodels.tsa.arima.model import ARIMA


def ensure_connection(func):
    def inner(*args, **kwargs):
        with sqlite3.connect('data.db') as con:
            res = func(*args, conn=con, **kwargs)
        return res

    return inner


@ensure_connection
def init_db(conn):
    # conn = get_connection()
    c = conn.cursor()
    c.execute('DROP TABLE IF EXISTS expenses')
    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY UNIQUE, 
        user_id INTEGER NOT NULL,
        date TIMESTAMP,
        sum INTEGER,
        type INTEGER
        );''')

    conn.commit()


@ensure_connection
def add_money_transfer(conn, user_id: int, sum: int, type: int, date: int):
    c = conn.cursor()

    c.execute(f'INSERT INTO expenses (user_id, date, sum, type) VALUES (?, ?, ?, ?);', (user_id, date, sum, type))
    conn.commit()


def gen(t):
    return 1000 + 100 * math.sin(t / 150000) + 5 * ((-1) ** (random.randrange(1, 3))) * random.randrange(10)


def generate():
    t = 1583058006
    # 1583058006
    dt = 86400
    # секунд в 12 часах
    for i in range(100):
        t += dt
        s = gen(t)
        add_money_transfer(user_id=0, sum=s, type=0, date=t)


def arima_gen(y, p, q, d):
    arima_mod = ARIMA(y, order=(p, q, d))
    # print(type(arima_mod))
    arima_res = arima_mod.fit()
    return arima_res


def arima_model_sin():
    init_db()
    generate()
    # получим информацию из бд
    my_conn = sqlite3.connect('data.db')
    my_cursor = my_conn.cursor()
    my_cursor.execute("select date, sum from expenses")
    result = my_cursor.fetchall()
    dates = np.array([x[0] for x in result])
    sums = np.array([x[1] for x in result])

    # переформатируем
    str_start_date = pd.Timestamp(1583058006, unit='s', tz='US/Pacific').strftime('%Y-%m-%d')
    pd_dates = pd.date_range(str_start_date, freq=datetime.timedelta(seconds=86400), periods=100)
    str_dates = np.array([pd.Timestamp(d, unit='s').strftime('%Y-%m-%d') for d in dates])

    # строим
    # x = np.arange(1583058006, 1583058006 + 100 * 24 * 60 * 60, 1800)
    np_sums = np.sin(dates / 150000)
    np_sums *= 100
    np_sums += 1000
    # print(np_sums)
    pd_sums = pd.Series(sums, index=pd_dates)
    arima_res = arima_gen(pd_sums, 2, 0, 2)
    predicted_set = arima_res.predict()

    # вычисление среднеквадратической ошибки
    error = statsmodels.tools.eval_measures.rmse(predicted_set, pd_sums, axis=0)
    print(error)

    fig = plot_predict(arima_res, start="2020-05-01", end="2020-06-07")
    plt.figure(fig)
    print(arima_res.summary())

    plt.scatter(pd_dates, sums, c="red", linestyle="dotted")
    plt.plot(pd_dates, np_sums, c="green")
    # plt.ylim(500, 1500)
    # plt.xlim('2020-03-01', '2020-06-19')
    plt.show()


def arima_model_real_with_finding():
    all_data = pd.read_csv('indexed_preformatted.csv')
    sums = all_data[all_data.columns[-1]].values
    dates = all_data[all_data.columns[-2]].values

    normal_sums = []
    cur_date = dates[0]
    cur_sum = 0
    for i in range(len(sums)):
        if cur_date == dates[i]:
            cur_sum += sums[i]
        else:
            normal_sums.append(cur_sum)
            cur_sum = 0
            cur_date = dates[i]

    pd_dates = pd.date_range(dates[0], freq=datetime.timedelta(days=1), periods=len(normal_sums))

    pd_sums_series = pd.Series(normal_sums, index=pd_dates)
    print(pd_sums_series)
    # перебор значений
    # min_error = 1000000000
    # min_p = 50
    # for i in range(10, 50):
    #     arima_res = arima_gen(pd_sums_series, i, 0, 1)
    #     predicted_set = arima_res.predict()
    #     error = statsmodels.tools.eval_measures.rmse(predicted_set, pd_sums_series, axis=0)
    #     if error < min_error:
    #         min_error = error
    #         min_p = i
    # print(min_p, min_error)
    # fig = plot_predict(arima_res, start="2017-05-14", end="2019-11-04")
    # plt.figure(fig)
    plt.scatter(dates, sums, c="red", linestyle="dotted")
    plt.ylim(0, 25000)
    plt.xlim('2016-11-02', '2019-11-04')
    plt.show()


def arima_model_real():
    all_data = pd.read_csv('personal_transactions.csv')
    # print(all_data.head())
    sums = []
    dates = []
    for i in range(len(all_data[all_data.columns[2]].values)):
        if ((all_data[all_data.columns[3]].values[i] == "debit") and (all_data[all_data.columns[2]].values[i]
                                                                      < 7000)):
            sums.append(all_data[all_data.columns[2]].values[i])
            dates.append(all_data[all_data.columns[0]].values[i])
    print(len(sums))

    normal_sums = []

    cur_date = dates[0]
    cur_sum = 0
    for i in range(len(sums)):
        if cur_date == dates[i]:
            cur_sum += sums[i]
        else:
            normal_sums.append(cur_sum)
            cur_sum = 0
            cur_date = dates[i]
    pd_dates = pd.date_range(dates[0], freq=datetime.timedelta(days=1), periods=len(normal_sums))
    print(pd_dates[100])

    # предсказание
    pd_sums = pd.Series(normal_sums, index=pd_dates)
    arima_res = arima_gen(pd_sums, 2, 0, 2)
    predicted_set = arima_res.predict()
    fig = plot_predict(arima_res, start="2018-01-01", end="2019-01-01")
    # print(type(fig))
    plt.figure(fig)

    print(len(pd_dates), len(normal_sums))
    plt.scatter(pd_dates, normal_sums, c="red", linestyle="dotted")
    plt.xlim('2018-01-01', '2019-05-01')
    plt.show()


if __name__ == '__main__':
    arima_model_sin()
