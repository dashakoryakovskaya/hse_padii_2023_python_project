import sqlite3
import db
import config
import predict

import telebot
from telebot import types

from pathlib import Path
import os

from threading import Thread

import datetime
import time
# from notifiers import get_notifier
import schedule

import cv2
import os

from fns import FnsAccess
import fns
import requests
import json

import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('agg')

import seaborn as sns
custom_params = {'patch.force_edgecolor': False}
sns.set_theme(rc=custom_params)

tconv = lambda x: time.strftime("%Y-%m-%d", time.localtime(x))
tconv_time = lambda x: time.strftime("%H:%M", time.localtime(x))

STOP_BOT_FLAG = False

bot = telebot.TeleBot(config.token)


def html_to_jpg(chat_id, user_id, type, ex_in, all_period=False, data_start='', data_end=''):
    with open(f'files/{chat_id}/statistic.html', 'w') as ind:
        # print(db.get_all_statistic(user_id=user_id, type=type, ex_in=ex_in, all_period=all_period, data_start=data_start, data_end=data_end).get_string())
        ind.write(
            f'<meta charset="Windows-1251" /><pre>{db.get_all_statistic(user_id=user_id, type=type, ex_in=ex_in, all_period=all_period, data_start=data_start, data_end=data_end).get_string()}</pre>')
    bot.send_document(chat_id, open(f'files/{chat_id}/statistic.html', 'rb'))
    os.remove(f'files/{chat_id}/statistic.html')


def list_of_tuples_to_str(list_tup: list):
    string = ''
    for row in list_tup:
        string += ' '.join(map(str, row)) + '\n'
    return string


def one_tuple_to_str(tup: tuple):
    return str(tup[0][0])


def daily_notification(user_id, text, category):
    if category != -1:
        key = types.InlineKeyboardMarkup()
        key.add(types.InlineKeyboardButton(text="Хочу внести расходы", callback_data="ex_" + str(category)))
        bot.send_message(user_id, text, reply_markup=key)
    else:
        bot.send_message(user_id, text)


def monthly_notification(user_id, text, date, category):
    if datetime.now().day == date and category == -1:
        bot.send_message(user_id, text)
    elif datetime.now().day == date and category != -1:
        key = types.InlineKeyboardMarkup()
        key.add(types.InlineKeyboardButton(text="Хочу внести расходы", callback_data="ex_" + str(category)))
        bot.send_message(user_id, text, reply_markup=key)


def notify():
    while not STOP_BOT_FLAG:
        schedule.run_pending()
        time.sleep(1)


def create_notification(notification_id, notification_type, user_id, text, date, time, category):
    # schedule.every(5).seconds.do(daily_notification, user_id, text).tag(notification_id)
    # print(time[:-3])
    # print(date[8:])
    if notification_type == 0:
        schedule.every().day.at(time[:-3]).do(daily_notification, user_id, text, category).tag(notification_id)
    else:
        schedule.every().day.at(time[:-3]).do(monthly_notification, user_id, text, date, category).tag(notification_id)


def cancel_notification(notification_id: int):
    schedule.clear(notification_id)


# меню для главного меню и категорий
def menu_key():
    key = types.InlineKeyboardMarkup()
    but_1 = types.InlineKeyboardButton(text="📉 Расходы", callback_data="ex")
    but_2 = types.InlineKeyboardButton(text="📈 Доходы", callback_data="in")
    but_3 = types.InlineKeyboardButton(text="📃 Статистика", callback_data="data")
    but_4 = types.InlineKeyboardButton(text="✔️ Дисконтные карты", callback_data="cards")
    but_5 = types.InlineKeyboardButton(text="🔔 Напоминания", callback_data="remind")
    but_6 = types.InlineKeyboardButton(text="🪄 Предсказания расходов", callback_data="predict")
    key.add(but_1, but_2, but_3, but_4, but_5, but_6)
    return key


def category_key(user_id, ex_in, callback):
    key = types.InlineKeyboardMarkup()
    cat_dict = db.get_categories(ex_in=ex_in)
    for key_d in cat_dict.keys():
        key.add(types.InlineKeyboardButton(text=key_d, callback_data=callback + str(cat_dict[key_d])))
    key.add(types.InlineKeyboardButton(text="📌 Меню", callback_data="menu"))
    return key


@bot.message_handler(commands=['start'])
def start_message(message):
    bot.clear_step_handler_by_chat_id(chat_id=message.chat.id)
    bot.send_message(message.chat.id, "Привет ✌️ Я - бот для отслеживания твоих финансов!", reply_markup=menu_key())
    db.add_user(user_id=message.from_user.id, name=message.from_user.username)


@bot.message_handler(commands=['help'])
def start_message(message):
    bot.clear_step_handler_by_chat_id(chat_id=message.chat.id)
    bot.send_message(message.chat.id, "📉 Расходы - добавление расходов \n"
                                      "📈 Доходы - добавление доходов \n"
                                      "📃 Статистика - баланс, все операции, диаграмма по категориям \n"
                                      "✔️ Дисконтные карты - добавление, получение и удаление карт \n"
                                      "🔔 Напоминания - добавление, просмотр и удаление напоминаний \n"
                                      "🪄 Предсказания расходов - предсказание расходов с помощью методов машинного обучения", reply_markup=menu_key())
    db.add_user(user_id=message.from_user.id, name=message.from_user.username)


def add_expenses_or_incomes_menu(message, user_id, type, ex_in):
    if message.text == "Считать qr код":
        bot.send_message(message.chat.id, 'Отправь мне фотографию qr кода', reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, lambda m: qr_code_reader(message=m, user_id=user_id, type=type))
    elif message.text.isdigit() and int(message.text) >= 0:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("Текущая дата"))
        mesg = bot.send_message(message.chat.id, "🗓️ Введите дату в формате YYYY-MM-DD или выберите текущую дату:",
                                reply_markup=markup)
        bot.register_next_step_handler(mesg, lambda m: add_date(message=m, user_id=user_id, type=type,
                                                                sum=int(message.text), ex_in=ex_in))
    else:
        mesg = bot.send_message(message.chat.id, "😥 Неправильный формат суммы\nВведите еще раз:")
        bot.register_next_step_handler(mesg,
                                       lambda m: add_expenses_or_incomes_menu(message=m, user_id=user_id,
                                                                              type=type, ex_in=ex_in))



def is_incorrect_date_format(string):
    try:
        valid_date = time.strptime(string, '%Y-%m-%d')
    except ValueError:
        return True
    return False
    '''return len(string) != 10 or string[4] != "-" or string[7] != "-" or not string[0:4].isdigit() \
        or not string[5:7].isdigit() or not string[8:10].isdigit() \
        or (12 < int(string[5:7]) or int(string[5:7]) < 1) \
        or (31 < int(string[8:10]) or int(string[8:10]) < 1) '''


def add_date(message, user_id, type, sum, ex_in):
    if message.text == "Текущая дата":
        # datetime.utcfromtimestamp(message.date).strftime('%Y-%m-%d')
        db.add_money_transfer(user_id=user_id, sum=sum, type=type,
                              date=tconv(message.date), ex_in=ex_in)
        bot.send_message(message.chat.id, text="Записано!", reply_markup=types.ReplyKeyboardRemove())
        bot.send_message(message.chat.id, text="📌 Меню", reply_markup=menu_key())
        return
    if is_incorrect_date_format(message.text):
        mesg = bot.send_message(message.chat.id, "😥 Неправильный формат YYYY-MM-DD\nВведите еще раз:")
        bot.register_next_step_handler(mesg, lambda m: add_date(message=m, user_id=user_id, type=type,
                                                                sum=sum, ex_in=ex_in))
    else:
        db.add_money_transfer(user_id=user_id, sum=sum, type=type, date=message.text, ex_in=ex_in)
        bot.send_message(message.chat.id, text="Записано!", reply_markup=types.ReplyKeyboardRemove())
        bot.send_message(message.chat.id, text="📌 Меню", reply_markup=menu_key())


def get_data_period(message, user_id, type, ex_in, sum_all, plot):
    Path(f'files/{message.chat.id}').mkdir(parents=True, exist_ok=True)
    if message.text == "Весь период":
        if plot == "pie":
            [y, lables] = db.get_sum_group(user_id=user_id, ex_in=ex_in, all_period=True, data_start='', data_end='')
            plt.pie(y, labels=lables)
            plt.savefig(f"files/{message.chat.id}/image.jpg")
            plt.clf()
            bot.send_photo(message.chat.id, photo=open(f"files/{message.chat.id}/image.jpg", 'rb'), reply_markup=types.ReplyKeyboardRemove())
            os.remove(f"files/{message.chat.id}/image.jpg")
        else:
            sum = db.get_sum(user_id=user_id, type=type, ex_in=ex_in, all_period=True)
            bot.send_message(message.chat.id, text="Сумма:\n" + str(sum), reply_markup=types.ReplyKeyboardRemove())
            if sum_all == "all":
                html_to_jpg(chat_id=message.chat.id, user_id=user_id, type=type, ex_in=ex_in, all_period=True)
        bot.send_message(message.chat.id, text="📌 Меню", reply_markup=menu_key())
        return
    if len(message.text) != 21 or is_incorrect_date_format(message.text[:10]) or is_incorrect_date_format(
            message.text[11:]) or message.text[10] != " " or message.text[:10] > message.text[11:]:
        mesg = bot.send_message(message.chat.id, "😥 Неправильный формат 'YYYY-MM-DD YYYY-MM-DD'\nВведите еще раз:")
        bot.register_next_step_handler(mesg,
                                       lambda m: get_data_period(message=m, user_id=user_id, type=type, ex_in=ex_in))
    else:
        data_start = message.text[:10]
        data_end = message.text[11:]
        if plot == "pie":
            [y, lables] = db.get_sum_group(user_id=user_id, ex_in=ex_in, all_period=False, data_start=data_start, data_end=data_end)
            plt.pie(y, labels=lables)
            plt.savefig(f"files/{message.chat.id}/image.jpg")
            plt.clf()
            bot.send_photo(message.chat.id, photo=open(f"files/{message.chat.id}/image.jpg", 'rb'), reply_markup=types.ReplyKeyboardRemove())
            os.remove(f"files/{message.chat.id}/image.jpg")
        else:
            sum = db.get_sum(user_id=user_id, type=type, ex_in=ex_in, all_period=False, data_start=data_start,
                             data_end=data_end)
            bot.send_message(message.chat.id, text="Сумма:\n" + str(sum), reply_markup=types.ReplyKeyboardRemove())
            if sum_all == "all":
                html_to_jpg(chat_id=message.chat.id, user_id=user_id, type=type, ex_in=ex_in, data_start=data_start, data_end=data_end)
        bot.send_message(message.chat.id, text="📌 Меню", reply_markup=menu_key())


def get_card_name(message, user_id, name):
    bot.clear_step_handler_by_chat_id(chat_id=message.chat.id)
    if message.content_type == 'text':
        mesg = bot.send_message(message.chat.id,
                                "Отправьте фото")
        bot.register_next_step_handler(mesg, lambda m: get_card_name(message=m, user_id=user_id, name=message.text))
    if message.content_type == 'photo':
        Path(f'files/{message.chat.id}/photos').mkdir(parents=True, exist_ok=True)
        file_info = bot.get_file(message.photo[len(message.photo) - 1].file_id)
        src = f'files/{message.chat.id}/' + file_info.file_path
        downloaded_file = bot.download_file(file_info.file_path)
        with open(src, 'wb') as f_d:
            f_d.write(downloaded_file)
        with open(src, 'rb') as f:
            binary = sqlite3.Binary(f.read())
        db.add_card(user_id=user_id, name=name, card=binary)
        os.remove(src)
        bot.send_message(message.chat.id, text="📌 Меню", reply_markup=menu_key())


def get_rem_data(message, user_id, type, cat):
    if 1 <= int(message.text) <= 31:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton("Текущее время")
        markup.add(btn1)
        mesg = bot.send_message(message.chat.id, "🕛 Введите время в формате HH:MM", reply_markup=markup)
        bot.register_next_step_handler(mesg,
                                       lambda m: get_rem_time(message=m, user_id=user_id, type=type,
                                                              cat=cat, day=int(message.text)))
    else:
        mesg = bot.send_message(message.chat.id, "😥 Неправильный формат день от 1 до 31\nВведите еще раз:")
        bot.register_next_step_handler(mesg, lambda m: get_rem_data(message=m, user_id=user_id, type=type, cat=cat))


def is_incorrect_time_format(string):
    return len(string) != 5 or string[2] != ":" or not string[:2].isdigit() \
        or not string[3:5].isdigit() or (24 <= int(string[:2]) or int(string[:2]) < 0) \
        or (60 <= int(string[3:]) or int(string[3:]) < 0)


def get_rem_time(message, user_id, type, cat, day=-1):
    if message.text != "Текущее время" and is_incorrect_time_format(message.text):
        mesg = bot.send_message(message.chat.id, "😥 Неправильный формат HH:MM\nВведите еще раз:")
        bot.register_next_step_handler(mesg, lambda m: get_rem_time(message=m, user_id=user_id, type=type, cat=cat, day=day))
    else:
        mesg = bot.send_message(message.chat.id, "Введите текст:", reply_markup=types.ReplyKeyboardRemove())
        time = message.text if message.text != "Текущее время" else tconv_time(message.date)
        bot.register_next_step_handler(mesg,
                                       lambda m: get_rem_text(message=m, user_id=user_id, type=type, cat=cat, day=day,
                                                              time=time))


def get_rem_text(message, user_id, type, cat, day, time):
    db.add_reminder(user_id=user_id, time=time + ":00", category=cat, date=day, text=message.text, type=type)
    bot.send_message(message.chat.id, text="📌 Меню", reply_markup=menu_key())


def get_pred_day(message, user_id, model):
    if not(message.text.isdigit()) or int(message.text) < 0:
        mesg = bot.send_message(message.chat.id, "😥 Неправильный формат\nВведите еще раз:")
        bot.register_next_step_handler(mesg, lambda m: get_pred_day(message=m, user_id=user_id, model=model))
    else:
        if model == "catboost":
            df = db.get_df(user_id=user_id)

            if 0.08 * df.shape[0] < 1:
                bot.send_message(message.chat.id, "Слишком мало информации о расходах :(")
                bot.send_message(message.chat.id, text="📌 Меню", reply_markup=menu_key())
                return

            str_start_date = pd.Timestamp(message.date, unit='s', tz='US/Pacific').strftime('%Y-%m-%d')
            pd_dates = pd.DataFrame(pd.date_range(str_start_date, freq=datetime.timedelta(seconds=86400), periods=int(message.text)))
            pd_dates.columns = ['date']

            res = predict.catboost(df=df, new_df=pd_dates)

            file = open(f"files/{message.chat.id}/predict{str_start_date}.txt", "w")
            for i, row in res.iterrows():
                file.write(f'{row["date"].date().strftime("%d-%m-%Y")} | {round(row["sum"], 3)}\n')
            file.close()
            bot.send_document(message.chat.id, open(f"files/{message.chat.id}/predict{str_start_date}.txt", "r"))
            os.remove(f"files/{message.chat.id}/predict{str_start_date}.txt")

            plt.scatter(res['date'], res['sum'], c="red", linestyle="dotted")
            plt.savefig(f"files/{message.chat.id}/image.jpg")
            plt.clf()
            bot.send_photo(message.chat.id, photo=open(f"files/{message.chat.id}/image.jpg", 'rb'))
            os.remove(f"files/{message.chat.id}/image.jpg")
        elif model == "lama":
            df = db.get_df(user_id=user_id)

            if 0.2 * df.shape[0] < 1:
                bot.send_message(message.chat.id, "Слишком мало информации о расходах :(")
                bot.send_message(message.chat.id, text="📌 Меню", reply_markup=menu_key())
                return


            str_start_date = pd.Timestamp(message.date, unit='s', tz='US/Pacific').strftime('%Y-%m-%d')
            pd_dates = pd.DataFrame(
                pd.date_range(str_start_date, freq=datetime.timedelta(seconds=86400), periods=int(message.text)))
            pd_dates.columns = ['date']
            res = predict.lama(df=df, new_df=pd_dates)

            file = open(f"files/{message.chat.id}/predict{str_start_date}.txt", "w")
            for i, row in res.iterrows():
                file.write(f'{row["date"].date().strftime("%d-%m-%Y")} | {round(row["sum"], 3)}\n')
            file.close()
            bot.send_document(message.chat.id, open(f"files/{message.chat.id}/predict{str_start_date}.txt", "r"))
            os.remove(f"files/{message.chat.id}/predict{str_start_date}.txt")

            plt.scatter(res['date'], res['sum'], c="red", linestyle="dotted")
            plt.savefig(f"files/{message.chat.id}/image.jpg")
            plt.clf()
            bot.send_photo(message.chat.id, photo=open(f"files/{message.chat.id}/image.jpg", 'rb'))
            os.remove(f"files/{message.chat.id}/image.jpg")

        elif model == "arima":
            df = db.get_df(user_id=user_id)
            df = df[['date', 'sum']]
            print(df)
            # df.columns = ['date', 'sum']
            df['date'] = pd.to_datetime(df['date'])
            grouped_df = df.groupby('date')['sum'].sum().reset_index()
            grouped_df = grouped_df.set_index('date')
            df = grouped_df.resample('D').fillna(method='ffill')
            df = df.reset_index()

            if df.shape[0] < 40:
                bot.send_message(message.chat.id, "Слишком мало информации о расходах :(")
                bot.send_message(message.chat.id, text="📌 Меню", reply_markup=menu_key())
                return

            print(str(message.date))
            start_date = pd.to_datetime(pd.Timestamp(message.date, unit='s', tz='US/Pacific').
                                        strftime('%Y-%m-%d')).date()
            days = int(message.text)

            # если использовать statsmodels
            # print(start_date, end_date)
            # df_train = df[df['date'] < start_date]
            # df_test = df[df['date'] >= start_date]
            # res = predict.arima(df=df, start_date=start_date, end_date=end_date, p=2, q=2, d=0)
            # print(res)
            # plt.figure(res)
            # plt.savefig(f"files/{message.chat.id}/image.jpg")
            # plt.clf()
            # bot.send_photo(message.chat.id, photo=open(f"files/{message.chat.id}/image.jpg", 'rb'))
            # os.remove(f"files/{message.chat.id}/image.jpg")

            # если использовать etna
            res, train_df = predict.arima_etna(df=df, days=days, p=10, q=0, d=0)
            if len(train_df) > 31:
                train_df = train_df[-30:]
            dates = pd.date_range(start_date, freq=datetime.timedelta(days=4), periods=len(res['target']))
            file = open(f"files/{message.chat.id}/predict{start_date}.txt", "w")
            for i, row in res.iterrows():
                file.write(f'{dates[i].date().strftime("%d-%m-%Y")} | {round(row["target"], 3)}\n')
            file.close()
            bot.send_document(message.chat.id, open(f"files/{message.chat.id}/predict{start_date}.txt", "r"))
            os.remove(f"files/{message.chat.id}/predict{start_date}.txt")

            plt.plot(train_df['timestamp'], train_df['target'], c="rosybrown", linestyle=":")
            plt.plot(res['timestamp'], res['target'], c="cornflowerblue", linestyle="-")
            plt.savefig(f"files/{message.chat.id}/image.jpg")
            plt.clf()
            bot.send_photo(message.chat.id, photo=open(f"files/{message.chat.id}/image.jpg", 'rb'))
            os.remove(f"files/{message.chat.id}/image.jpg")

        elif model == "prophet":
            df = db.get_df(user_id=user_id)
            df = df[['date', 'sum']]
            df['date'] = pd.to_datetime(df['date'])
            grouped_df = df.groupby('date')['sum'].sum().reset_index()
            grouped_df = grouped_df.set_index('date')
            df = grouped_df.resample('D').fillna(method='ffill')
            df = df.reset_index()

            if df.shape[0] < 40:
                bot.send_message(message.chat.id, "Слишком мало информации о расходах :(")
                bot.send_message(message.chat.id, text="📌 Меню", reply_markup=menu_key())
                return

            start_date = pd.to_datetime(pd.Timestamp(message.date, unit='s', tz='US/Pacific').
                                        strftime('%Y-%m-%d')).date()
            days = int(message.text)

            # если использовать etna
            res, train_df = predict.prophet_etna(df=df, days=days, real_dates=False)
            if len(train_df) > 31:
                train_df = train_df[-30:]
            dates = pd.date_range(start_date, freq=datetime.timedelta(days=4), periods=len(res['target']))
            file = open(f"files/{message.chat.id}/predict{start_date}.txt", "w")
            for i, row in res.iterrows():
                file.write(f'{dates[i].date().strftime("%d-%m-%Y")} | {round(row["target"], 3)}\n')
            file.close()
            bot.send_document(message.chat.id, open(f"files/{message.chat.id}/predict{start_date}.txt", "r"))
            os.remove(f"files/{message.chat.id}/predict{start_date}.txt")

            plt.plot(train_df['timestamp'], train_df['target'], c="rosybrown", linestyle=":")
            plt.plot(res['timestamp'], res['target'], c="cornflowerblue", linestyle="-")
            plt.savefig(f"files/{message.chat.id}/image.jpg")
            plt.clf()
            bot.send_photo(message.chat.id, photo=open(f"files/{message.chat.id}/image.jpg", 'rb'))
            os.remove(f"files/{message.chat.id}/image.jpg")

        elif model == "prophet_2":
            df = db.get_df(user_id=user_id)
            df = df[['date', 'sum']]
            df['date'] = pd.to_datetime(df['date'])
            grouped_df = df.groupby('date')['sum'].sum().reset_index()
            grouped_df = grouped_df.set_index('date')
            df = grouped_df.resample('D').fillna(method='ffill')
            df = df.reset_index()

            if df.shape[0] < 10:
                bot.send_message(message.chat.id, "Слишком мало информации о расходах :(")
                bot.send_message(message.chat.id, text="📌 Меню", reply_markup=menu_key())
                return

            start_date = pd.to_datetime(pd.Timestamp(message.date, unit='s', tz='US/Pacific').
                                        strftime('%Y-%m-%d')).date()
            days = int(message.text)

            # если использовать etna
            res, train_df = predict.prophet_etna(df=df, days=days, real_dates=True)
            if len(train_df) > 31:
                train_df = train_df[-30:]
            dates = pd.date_range(start_date, freq=datetime.timedelta(days=1), periods=len(res['target']))
            file = open(f"files/{message.chat.id}/predict{start_date}.txt", "w")
            for i, row in res.iterrows():
                file.write(f'{dates[i].date().strftime("%d-%m-%Y")} | {round(row["target"], 3)}\n')
            file.close()
            bot.send_document(message.chat.id, open(f"files/{message.chat.id}/predict{start_date}.txt", "r"))
            os.remove(f"files/{message.chat.id}/predict{start_date}.txt")

            plt.plot(train_df['timestamp'], train_df['target'], c="rosybrown", linestyle=":")
            plt.plot(res['timestamp'], res['target'], c="cornflowerblue", linestyle="-")
            plt.savefig(f"files/{message.chat.id}/image.jpg")
            plt.clf()
            bot.send_photo(message.chat.id, photo=open(f"files/{message.chat.id}/image.jpg", 'rb'))
            os.remove(f"files/{message.chat.id}/image.jpg")

        bot.send_message(message.chat.id, text="📌 Меню", reply_markup=menu_key())


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
    if call.message:
        bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
        if call.data == "menu":
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="📌 Меню",
                                  reply_markup=menu_key())
        if call.data == "ex" or call.data == "in":
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="📎 Выберите категорию:",
                                  reply_markup=category_key(user_id=call.from_user.id, ex_in=call.data,
                                                            callback=call.data + "_"))

        if call.data[:len("ex_")] == "ex_" or call.data[:len("in_")] == "in_":
            if (call.data[:len("ex_")] == "ex_"):
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                markup.add(types.KeyboardButton("Считать qr код"))
                mesg = bot.send_message(call.message.chat.id, "💰 Введите сумму или считайте qr код",
                                        reply_markup=markup)
            else:
                mesg = bot.send_message(call.message.chat.id, "💰 Введите сумму")
            bot.register_next_step_handler(mesg,
                                           lambda m: add_expenses_or_incomes_menu(message=m, user_id=call.from_user.id,
                                                                                  type=call.data[len("ex_"):],
                                                                                  ex_in=call.data[:2]))

        if call.data == "data":
            key = types.InlineKeyboardMarkup()
            but_1 = types.InlineKeyboardButton(text="💰 Баланс", callback_data="data_balance")
            but_2 = types.InlineKeyboardButton(text="📉 Расходы", callback_data="data_ex")
            but_3 = types.InlineKeyboardButton(text="📈 Доходы", callback_data="data_in")
            but_4 = types.InlineKeyboardButton(text="📊 Расходы - диаграмма", callback_data="data_ex_pie")
            but_5 = types.InlineKeyboardButton(text="📊 Доходы - диаграмма", callback_data="data_in_pie")
            but_6 = types.InlineKeyboardButton(text="📌 Меню", callback_data="menu")
            key.add(but_1, but_2, but_3, but_4, but_5, but_6)
            # bot.send_message(chat_id=call.message.chat.id, text="Выберите категорию:", reply_markup=key)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="📎 Выберите категорию:", reply_markup=key)

        # data_ex_numcat_all
        if call.data == "data_balance":
            bot.send_message(call.message.chat.id, 'Баланс:' + '\n' + one_tuple_to_str(
                db.sql_execute(sql=f"SELECT total FROM balance WHERE user_id={call.from_user.id};")))
            bot.send_message(call.message.chat.id, text="📌 Меню", reply_markup=menu_key())

        if call.data == "data_ex" or call.data == "data_in":
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="📎 Выберите категорию:",
                                  reply_markup=category_key(user_id=call.from_user.id, ex_in=call.data[5:],
                                                            callback=call.data + "_").add(
                                      types.InlineKeyboardButton(text="📎 Все категории",
                                                                 callback_data=call.data + "_all")))

        if call.data.count("_") == 2 and (
                call.data[:len("data_ex_")] == "data_ex_" or call.data[:len("data_in_")] == "data_in_"):
            key = types.InlineKeyboardMarkup()
            but_1 = types.InlineKeyboardButton(text="💰 Сумма", callback_data=call.data + "_sum")
            but_2 = types.InlineKeyboardButton(text="📃 Все операции", callback_data=call.data + "_all")
            but_3 = types.InlineKeyboardButton(text="📌 Меню", callback_data="menu")
            key.add(but_1, but_2, but_3)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="Выберите тип:",
                                  reply_markup=key)

        if call.data == "data_ex_pie" or call.data == "data_in_pie" or call.data.count("_") == 3 and (
                call.data[:len("data_ex_")] == "data_ex_" or call.data[:len("data_in_")] == "data_in_") and (
                call.data[-4:] == "_sum" or call.data[-4:] == "_all"):
            bot.answer_callback_query(call.id, "Введите период")
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            btn1 = types.KeyboardButton("Весь период")
            markup.add(btn1)
            mesg = bot.send_message(call.message.chat.id,
                                    "🗓️ Введите период в формате 'YYYY-MM-DD YYYY-MM-DD' или выберите весь период:",
                                    reply_markup=markup)
            bot.register_next_step_handler(mesg,
                                           lambda m: get_data_period(message=m, user_id=call.from_user.id,
                                                                     type=-1 if call.data[
                                                                                len("data_ex_"):call.data.rfind(
                                                                                    "_")] == "all" else call.data[
                                                                                                        len("data_ex_"):call.data.rfind(
                                                                                                            "_")],
                                                                     ex_in=call.data[5:7], sum_all=call.data[-3:], plot="pie" if call.data[8:] == "pie" else ""))

        if call.data == "cards":
            key = types.InlineKeyboardMarkup()
            but_1 = types.InlineKeyboardButton(text="📃 Получить карту", callback_data="cards_get")
            but_2 = types.InlineKeyboardButton(text="✅ Добавить карту", callback_data="cards_add")
            but_3 = types.InlineKeyboardButton(text="❌ Удалить карту", callback_data="cards_del")
            but_4 = types.InlineKeyboardButton(text="📌 Меню", callback_data="menu")
            key.add(but_1, but_2, but_3, but_4)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="📎 Выберите действие:",
                                  reply_markup=key)

        if call.data == "cards_add":
            mesg = bot.send_message(call.message.chat.id, "✔️ Введите название")
            bot.register_next_step_handler(mesg, lambda m: get_card_name(message=m, user_id=call.from_user.id, name=""))

        if call.data == "cards_get":
            key = types.InlineKeyboardMarkup()
            for line in db.get_cards(user_id=call.from_user.id):
                key.add(types.InlineKeyboardButton(text=line[0], callback_data="cards_get_" + line[0]))
            key.add(types.InlineKeyboardButton(text="📌 Меню", callback_data="menu"))
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="✔️ Выберите магазин:",
                                  reply_markup=key)

        if len(call.data) >= len("cards_get_") and call.data[:len("cards_get_")] == "cards_get_":
            for line in db.get_cards(user_id=call.from_user.id):
                if line[0] == call.data[len("cards_get_"):]:
                    bot.send_photo(chat_id=call.message.chat.id, photo=line[1])
                    # with open("files/image.jpg", "wb") as f:
                    #     f.write(line[1])
                    #     bot.send_photo(chat_id=call.message.chat.id, photo=open("files/image.jpg", "rb"))
                    break
            bot.send_message(call.message.chat.id, text="📌 Меню", reply_markup=menu_key())

        if call.data == "cards_del":
            key = types.InlineKeyboardMarkup()
            list_rem = db.get_all_cards_name(user_id=call.from_user.id)
            for l in list_rem:
                key.add(types.InlineKeyboardButton(text=l[0], callback_data="cards_del_" + str(l[0])))
            key.add(types.InlineKeyboardButton(text="📌 Меню", callback_data="menu"))
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="Выберите карту:",
                                  reply_markup=key)

        if call.data[:len("cards_del_")] == "cards_del_":
            db.erase_card(user_id=call.from_user.id, name=call.data[len("cards_del_"):])
            bot.send_message(call.message.chat.id, text="📌 Меню", reply_markup=menu_key())

        if call.data == "remind":
            key = types.InlineKeyboardMarkup()
            but_1 = types.InlineKeyboardButton(text="✅ Добавить напоминание", callback_data=call.data + "_add")
            but_2 = types.InlineKeyboardButton(text="❌ Удалить напоминание", callback_data=call.data + "_del")
            but_3 = types.InlineKeyboardButton(text="📌 Меню", callback_data="menu")
            key.add(but_1, but_2, but_3)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="Выберите действие:",
                                  reply_markup=key)

        if call.data == "remind_add":
            key = types.InlineKeyboardMarkup()
            but_1 = types.InlineKeyboardButton(text="Каждый день", callback_data=call.data + "_0")
            but_2 = types.InlineKeyboardButton(text="Каждый месяц", callback_data=call.data + "_1")
            but_3 = types.InlineKeyboardButton(text="📌 Меню", callback_data="menu")
            key.add(but_1, but_2, but_3)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="Выберите частоту:",
                                  reply_markup=key)

        if call.data == "remind_add_0" or call.data == "remind_add_1":
            but_1 = types.InlineKeyboardButton(text="Напоминание", callback_data=call.data + "_-1")
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="Выберите категорию трат или напоминание о заполнении:",
                                  reply_markup=category_key(user_id=call.from_user.id, ex_in="ex",
                                                            callback=call.data + "_").add(but_1))

        if call.data[:len("remind_add_1_")] == "remind_add_1_" and call.data.count("_") == 3:
            mesg = bot.send_message(call.message.chat.id, "🗓️ Введите день (число от 1 до 31)")
            bot.register_next_step_handler(mesg,
                                           lambda m: get_rem_data(message=m, user_id=call.from_user.id, type=1,
                                                                  cat=call.data[
                                                                      len("remind_add_1_"):]))

        if call.data[:len("remind_add_0_")] == "remind_add_0_" and call.data.count("_") == 3:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            btn1 = types.KeyboardButton("Текущее время")
            markup.add(btn1)
            mesg = bot.send_message(call.message.chat.id, "🕛 Введите время в формате HH:MM", reply_markup=markup)
            bot.register_next_step_handler(mesg,
                                           lambda m: get_rem_time(message=m, user_id=call.from_user.id, type=0,
                                                                  cat=call.data[
                                                                      len("remind_add_0_"):]))

        if call.data == "remind_del":
            key = types.InlineKeyboardMarkup()
            list_rem = db.get_all_reminders(user_id=call.from_user.id)
            for l in list_rem:
                text = db.sql_execute(sql=f"SELECT text FROM reminders_text WHERE id = {l[0]}")[0][0]
                key.add(types.InlineKeyboardButton(text=text[:20] + ("... " if len(text) > 20 else " ") + l[3][:5] + (
                    " " + str(l[2]) if l[1] == 1 else ""), callback_data="remind_del_" + str(l[0])))
            key.add(types.InlineKeyboardButton(text="📌 Меню", callback_data="menu"))
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="Выберите напоминание:",
                                  reply_markup=key)

        if call.data[:len("remind_del_")] == "remind_del_":
            db.erase_reminder(notification_id=int(call.data[len("remind_del_"):]))
            bot.send_message(call.message.chat.id, text="📌 Меню", reply_markup=menu_key())

        if call.data == "predict":
            key = types.InlineKeyboardMarkup()
            but_1 = types.InlineKeyboardButton(text="catboost", callback_data="predict_catboost")
            but_2 = types.InlineKeyboardButton(text="lama", callback_data="predict_lama")
            but_3 = types.InlineKeyboardButton(text="arima", callback_data="predict_arima")
            but_4 = types.InlineKeyboardButton(text="prophet-1", callback_data="predict_prophet")
            but_5 = types.InlineKeyboardButton(text="prophet-2", callback_data="predict_prophet_2")
            but_6 = types.InlineKeyboardButton(text="📌 Меню", callback_data="menu")
            key.add(but_1, but_2, but_3, but_4, but_5, but_6)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="Описание моделей:\n\n"
                                       "🤌*catboost*\nподходит для предсказаний на длительный период\n\n"
                                       "🤌*lama*\nвысокая точность предсказания больших трат\n\n"
                                       "🤌*arima*\nподходит для предсказания на небольшой период, "
                                       "предказывается каждый четвертый день, виден характер трат\n\n"
                                       "🤌*prophet-1*\nподходит для предсказания тренда трат, предказывается "
                                       "каждый четвертый день\n\n"
                                       "🤌*prophet-2*\nподходит для предсказания тренда трат, предказывается"
                                       " каждый день\n"
                                       "\nВыберите модель:",
                                  reply_markup=key, parse_mode="Markdown")

        if call.data[:len("predict_")] == "predict_":
            mesg = bot.send_message(call.message.chat.id, "Введите количество дней для предсказания")
            bot.register_next_step_handler(mesg,
                                           lambda m: get_pred_day(message=m, user_id=call.from_user.id, model=call.data[len("predict_"):]))


@bot.message_handler(content_types=["text"])
def messages(message):
    # вся информация из таблицы по запросу имятаблицы_data
    if message.text[-4:] == 'data':
        bot.send_message(message.chat.id, message.text + ':\n' + list_of_tuples_to_str(db.sql_execute(sql="SELECT * "
                                                                                                          "FROM " +
                                                                                                          message.text[
                                                                                                          :-5])))
    if message.text == 'check balance':
        bot.send_message(message.chat.id, 'Баланс:' + '\n' + one_tuple_to_str(
            db.sql_execute(sql=f"SELECT total FROM balance WHERE user_id={message.from_user.id};")))

    if message.text == 'add notification':
        db.add_reminder(user_id=message.chat.id, date=11, time='20:17:00', type=1, text='Срочно оплати')

    if message.text == 'delete notification':
        bot.send_message(message.chat.id, 'balance' + ':\n' + one_tuple_to_str(
            db.sql_execute(sql=f"SELECT total FROM balance WHERE user_id={message.from_user.id};")))
    if message.text[0:2] == 'qr':
        bot.send_message(message.chat.id,
                         'Отправь мне фотографию qr кода')
        bot.register_next_step_handler(message, qr_code_reader)


def qr_get_phone(message, qr_code, user_id, type):
    phone = str(message.text)
    if len(phone) != 12 or phone[0:2] != "+7" or not (phone[2:].isdigit()):
        mesg = bot.send_message(message.chat.id, "😥 Неправильный формат '+7'\nВведите еще раз:")
        bot.register_next_step_handler(mesg,
                                       lambda m: qr_get_phone(message=m, qr_code=qr_code, user_id=user_id,
                                                              type=type))
    else:
        url = f'https://{fns.HOST}/v2/auth/phone/request'
        payload = {
            'phone': phone,
            'client_secret': fns.CLIENT_SECRET,
            'os': fns.OS
        }
        try:
            resp = requests.post(url, json=payload, headers=fns.headers)
            if resp.status_code == 429:
                bot.send_message(message.chat.id, 'Слишком много запросов, попробуйте позже')
                raise Exception('Слишком много запросов')
            mesg = bot.send_message(chat_id=message.chat.id, text="Введите код из смс: ")
            bot.register_next_step_handler(mesg, lambda m: qr_get_code(message=m, phone=message.text, qr_code=qr_code, user_id=user_id, type=type))
        except Exception as e:
            print(e)
            bot.send_message(message.chat.id, 'Возможно qr код не содержит нужную информацию. Попробуйте еще раз :(', reply_markup=menu_key())


def qr_get_code(message, phone, qr_code, user_id, type):
    code = str(message.text)
    url = f'https://{fns.HOST}/v2/auth/phone/verify'
    payload = {
        'phone': phone,
        'client_secret': fns.CLIENT_SECRET,
        'code': code,
        "os": fns.OS
    }
    resp = requests.post(url, json=payload, headers=fns.headers)
    try:
        client = FnsAccess(chat_id=message.chat.id, phone=phone, code=code, session_id=resp.json()['sessionId'],
                           refresh_token=resp.json()['refresh_token'])
        ticket = client.get_ticket(qr_code)
        elements = ticket["ticket"]["document"]["receipt"]["items"]
        totalItems = []
        for el in elements:
            print(el["name"] + ' ' + str((el["sum"] + 99) // 100), end='\n')
            totalItems.append(
                el["name"] + ' ' + str((el["sum"] + 99) // 100))  # копейки в рубли с округлением вверх
        totalSum = str((ticket["ticket"]["document"]["receipt"]["totalSum"] + 99) // 100)
        print(totalSum, end='\n')
        bot.send_message(message.chat.id, totalSum)
        client.refresh_token_function()
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("Текущая дата"))
        mesg = bot.send_message(message.chat.id, "🗓️ Введите дату в формате YYYY-MM-DD или выберите текущую дату:",
                                reply_markup=markup)
        bot.register_next_step_handler(mesg, lambda m: add_date(message=m, user_id=user_id, type=type,
                                                                sum=totalSum, ex_in="ex"))
    except Exception as e:
        print(e)
        mesg = bot.send_message(message.chat.id, 'Попробуйте еще раз :(')
        bot.register_next_step_handler(mesg,
                                       lambda m: qr_get_code(message=m, phone=phone, qr_code=qr_code,
                                                             user_id=user_id, type=type))


@bot.message_handler(content_types=['photo', 'document'])
def qr_code_reader(message, user_id, type):
    Path('photos').mkdir(parents=True, exist_ok=True)
    file_info = bot.get_file(message.photo[len(message.photo) - 1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    src = file_info.file_path

    with open(src, 'wb') as new_file:
        new_file.write(downloaded_file)

    try:
        img_qr = cv2.imread(src)
        detector = cv2.QRCodeDetector()
        data, bbox, clear_qr = detector.detectAndDecode(img_qr)
        qr_code = data
        print(qr_code)
        if qr_code == "":
            bot.send_message(message.chat.id, 'QR код не считан')
            raise Exception('QR код не считан')
        bot.send_message(message.chat.id, 'Успешно!')
        mesg = bot.send_message(message.chat.id, "Введите номер телефона в формате '+7': ")
        bot.register_next_step_handler(mesg,
                                       lambda m: qr_get_phone(message=m, qr_code=qr_code,
                                                              user_id=user_id, type=type))
        os.remove(file_info.file_path)  # удаление изображения с чеком после распознавания
    except Exception as e:
        os.remove(file_info.file_path)
        print(e)
        bot.send_message(message.chat.id, 'Попробуйте еще раз :(')
        bot.register_next_step_handler(message, lambda m: qr_code_reader(message=m, user_id=user_id, type=type))


def main():
    # TODO: добавить проверку соединения и тд
    th = Thread(target=notify)
    th.start()
    bot.polling()
    global STOP_BOT_FLAG
    STOP_BOT_FLAG = True
    th.join()


if __name__ == '__main__':
    # TODO: нужен ли тут flag_drop=True ?
    db.init_db(flag_drop=False)
    main()
