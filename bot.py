import sqlite3
import threading

import config
import telebot
import db
from telebot import types
from pathlib import Path

from datetime import datetime
import time

bot = telebot.TeleBot(config.token)

tconv = lambda x: time.strftime("%Y-%m-%d", time.localtime(x))


def list_of_tuples_to_str(list_tup: list):
    string = ''
    for row in list_tup:
        string += ' '.join(map(str, row)) + '\n'
    return string


def one_tuple_to_str(tup: tuple):
    return str(tup[0][0])


# меню для главного меню и категорий
def menu_key():
    key = types.InlineKeyboardMarkup()
    but_1 = types.InlineKeyboardButton(text="📉 Расходы", callback_data="ex")
    but_2 = types.InlineKeyboardButton(text="📈 Доходы", callback_data="in")
    but_3 = types.InlineKeyboardButton(text="📃 Статистика", callback_data="data")
    but_4 = types.InlineKeyboardButton(text="✔️ Дисконтные карты", callback_data="cards")
    key.add(but_1, but_2, but_3, but_4)
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
    bot.send_message(message.chat.id, "Привет ✌️ Я - бот для отслеживания твоих финансов!", reply_markup=menu_key())
    db.add_user(user_id=message.from_user.id, name=message.from_user.first_name)
    # bot.send_message(message.chat.id, str(threading.current_thread().ident))


# TODO: нужна /stop команда?
@bot.message_handler(commands=['stop'])
def stop(message):
    bot.send_message(message.chat.id, "До встречи!")
    bot.stop_polling()


def add_expenses_or_incomes_menu(message, user_id, type, ex_in):
    if message.text.isdigit() and int(message.text) >= 0:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton("Текущая дата")
        markup.add(btn1)
        mesg = bot.send_message(message.chat.id, "🗓️ Введите дату в формате YYYY-MM-DD или выберите текущую дату:",
                                reply_markup=markup)
        bot.register_next_step_handler(mesg, lambda m: add_date(message=m, user_id=user_id, type=type,
                                                                sum=int(message.text), ex_in=ex_in))
    else:
        mesg = bot.send_message(message.chat.id, "😥 Неправильный формат суммы\nВведите еще раз:")
        bot.register_next_step_handler(mesg,
                                       lambda m: add_expenses_or_incomes_menu(message=m, user_id=user_id,
                                                                              type=type, ex_in=ex_in))

    # TODO: проверять длину месяца (апрель - 30 и тд)


def is_incorrect_date_format(string):
    return len(string) != 10 or string[4] != "-" or string[7] != "-" or not string[0:4].isdigit() \
        or not string[5:7].isdigit() or not string[8:10].isdigit() \
        or (12 < int(string[5:7]) or int(string[5:7]) < 1) \
        or (31 < int(string[8:10]) or int(string[8:10]) < 1)


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


def get_data_period(message, user_id, type, ex_in, sum_all):
    if message.text == "Весь период":
        sum = db.get_sum(user_id=user_id, type=type, ex_in=ex_in, all_period=True)
        bot.send_message(message.chat.id, text="Сумма:\n" + str(sum), reply_markup=types.ReplyKeyboardRemove())
        if sum_all == "all":
            bot.send_message(message.chat.id,
                             text=f'<pre>{db.get_all_statistic(user_id=user_id, type=type, ex_in=ex_in, all_period=True).get_string()}</pre>',
                             parse_mode="HTML")
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
        sum = db.get_sum(user_id=user_id, type=type, ex_in=ex_in, all_period=False, data_start=data_start,
                         data_end=data_end)
        bot.send_message(message.chat.id, text="Сумма:\n" + str(sum), reply_markup=types.ReplyKeyboardRemove())
        if sum_all == "all":
            bot.send_message(message.chat.id,
                             text=f'<pre>{db.get_all_statistic(user_id=user_id, type=type, ex_in=ex_in, data_start=data_start, data_end=data_end).get_string()}</pre>',
                             parse_mode="HTML")
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
        bot.send_message(message.chat.id, text="📌 Меню", reply_markup=menu_key())


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.message:
        if call.data == "menu":
            bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="📌 Меню",
                                  reply_markup=menu_key())
        if call.data == "ex" or call.data == "in":
            bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="📎 Выберите категорию:",
                                  reply_markup=category_key(user_id=call.from_user.id, ex_in=call.data,
                                                            callback=call.data + "_"))

        if call.data[:len("ex_")] == "ex_" or call.data[:len("in_")] == "in_":
            bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
            bot.answer_callback_query(call.id, "Введите сумму")
            mesg = bot.send_message(call.message.chat.id, "💰 Введите сумму")

            bot.register_next_step_handler(mesg,
                                           lambda m: add_expenses_or_incomes_menu(message=m, user_id=call.from_user.id,
                                                                                  type=call.data[len("ex_"):],
                                                                                  ex_in=call.data[:2]))

        if call.data == "data":
            bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
            # TODO: Продумать статистику для доходов и расходов (период, категории и тд)
            key = types.InlineKeyboardMarkup()
            but_1 = types.InlineKeyboardButton(text="💰 Баланс", callback_data="data_balance")
            but_2 = types.InlineKeyboardButton(text="📉 Расходы", callback_data="data_ex")
            but_3 = types.InlineKeyboardButton(text="📈 Доходы", callback_data="data_in")
            but_4 = types.InlineKeyboardButton(text="📌 Меню", callback_data="menu")
            key.add(but_1, but_2, but_3, but_4)
            # bot.send_message(chat_id=call.message.chat.id, text="Выберите категорию:", reply_markup=key)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="📎 Выберите категорию:", reply_markup=key)

        # data_ex_numcat_all
        if call.data == "data_balance":
            bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
            bot.send_message(call.message.chat.id, 'Баланс:' + '\n' + one_tuple_to_str(
                db.sql_execute(sql=f"SELECT total FROM balance WHERE user_id={call.from_user.id};")))
            bot.send_message(call.message.chat.id, text="📌 Меню", reply_markup=menu_key())

        if call.data == "data_ex" or call.data == "data_in":
            bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="📎 Выберите категорию:",
                                  reply_markup=category_key(user_id=call.from_user.id, ex_in=call.data[5:],
                                                            callback=call.data + "_").add(
                                      types.InlineKeyboardButton(text="📎 Все категории",
                                                                 callback_data=call.data + "_all")))

        if call.data.count("_") == 2 and (
                call.data[:len("data_ex_")] == "data_ex_" or call.data[:len("data_in_")] == "data_in_"):
            bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
            key = types.InlineKeyboardMarkup()
            but_1 = types.InlineKeyboardButton(text="💰 Сумма", callback_data=call.data + "_sum")
            but_2 = types.InlineKeyboardButton(text="📃 Все операции", callback_data=call.data + "_all")
            but_3 = types.InlineKeyboardButton(text="📌 Меню", callback_data="menu")
            key.add(but_1, but_2, but_3)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="Выберите тип:",
                                  reply_markup=key)

        if call.data.count("_") == 3 and (
                call.data[:len("data_ex_")] == "data_ex_" or call.data[:len("data_in_")] == "data_in_") and (
                call.data[-4:] == "_sum" or call.data[-4:] == "_all"):
            bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
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
                                                                     ex_in=call.data[5:7], sum_all=call.data[-3:]))

        if call.data == "cards":
            bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
            key = types.InlineKeyboardMarkup()
            but_1 = types.InlineKeyboardButton(text="📃 Получить карту", callback_data="cards_get")
            but_2 = types.InlineKeyboardButton(text="✅ Добавить карту", callback_data="cards_add")
            but_3 = types.InlineKeyboardButton(text="📌 Меню", callback_data="menu")
            key.add(but_1, but_2, but_3)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="📎 Выберите действие:",
                                  reply_markup=key)

        if call.data == "cards_add":
            bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
            mesg = bot.send_message(call.message.chat.id, "✔️ Введите название")
            bot.register_next_step_handler(mesg, lambda m: get_card_name(message=m, user_id=call.from_user.id, name=""))

        if call.data == "cards_get":
            bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
            key = types.InlineKeyboardMarkup()
            for line in db.get_cards(user_id=call.from_user.id):
                key.add(types.InlineKeyboardButton(text=line[0], callback_data="cards_get_" + line[0]))
            key.add(types.InlineKeyboardButton(text="📌 Меню", callback_data="menu"))
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="✔️ Выберите магазин:",
                                  reply_markup=key)

        if len(call.data) >= len("cards_get_") and call.data[:len("cards_get_")] == "cards_get_":
            bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
            for line in db.get_cards(user_id=call.from_user.id):
                if line[0] == call.data[len("cards_get_"):]:
                    bot.send_photo(chat_id=call.message.chat.id, photo=line[1])
                    # with open("files/image.jpg", "wb") as f:
                    #     f.write(line[1])
                    #     bot.send_photo(chat_id=call.message.chat.id, photo=open("files/image.jpg", "rb"))
                    break
            bot.send_message(call.message.chat.id, text="📌 Меню", reply_markup=menu_key())


@bot.message_handler(content_types=["text"])
def messages(message):
    # bot.send_message(message.chat.id, str(threading.current_thread().ident))
    '''if message.text[0] == '+':
        db.add_incomes(user_id=message.from_user.id, name=message.from_user.username, date=message.date,
                       sum=int(message.text[1:]), type='')
    if message.text[0] == '-':
        db.add_expenses(user_id=message.from_user.id, name=message.from_user.username, date=message.date,
                        sum=int(message.text[1:]), type='') '''
    # вся информация из таблицы по запросу имятаблицы_data
    if message.text[-4:] == 'data':
        bot.send_message(message.chat.id, message.text + ':\n' + list_of_tuples_to_str(db.sql_execute(sql="SELECT * "
                                                                                                          "FROM " +
                                                                                                          message.text[
                                                                                                          :-5])))
    if message.text == 'check balance':
        bot.send_message(message.chat.id, 'Баланс:' + '\n' + one_tuple_to_str(
            db.sql_execute(sql=f"SELECT total FROM balance WHERE user_id={message.from_user.id};")))


def main():
    # TODO: добавить проверку соединения и тд
    bot.polling()


if __name__ == '__main__':
    # TODO: нужен ли тут flag_drop=True ?
    db.init_db(flag_drop=True)
    main()
