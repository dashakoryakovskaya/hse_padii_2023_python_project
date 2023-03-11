from threading import Thread
import config
import telebot
import db
from telebot import types
from datetime import datetime
import time
# from notifiers import get_notifier
import schedule

bot = telebot.TeleBot(config.token)

tconv = lambda x: time.strftime("%Y-%m-%d", time.localtime(x))

STOP_BOT_FLAG = False


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
    but_5 = types.InlineKeyboardButton(text="🔔 Напоминания", callback_data="remind")
    key.add(but_1, but_2, but_3, but_5)
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


def get_rem_data(message, user_id, type, cat):
    if 1 <= int(message.text) <= 31:
        mesg = bot.send_message(message.chat.id, "🕛 Введите время в формате HH:MM:SS")
        bot.register_next_step_handler(mesg,
                                       lambda m: get_rem_time(message=m, user_id=user_id, type=type,
                                                              cat=cat, day=int(message.text)))
    else:
        mesg = bot.send_message(message.chat.id, "😥 Неправильный формат день от 1 до 31\nВведите еще раз:")
        bot.register_next_step_handler(mesg,
                                       lambda m: get_rem_data(message=m, user_id=user_id, type=type, cat=cat))


def is_incorrect_time_format(string):
    return len(string) != 8 or string[2] != ":" or string[5] != ":" or not string[:2].isdigit() \
        or not string[3:5].isdigit() or not string[6:].isdigit() or (24 <= int(string[:2]) or int(string[:2]) < 0) \
        or (60 <= int(string[3:5]) or int(string[3:5]) < 0) or (60 <= int(string[6:]) or int(string[6:]) < 0)


def get_rem_time(message, user_id, type, cat, day=-1):
    if is_incorrect_time_format(message.text):
        mesg = bot.send_message(message.chat.id, "😥 Неправильный формат HH:MM:SS\nВведите еще раз:")
        bot.register_next_step_handler(mesg,
                                       lambda m: get_rem_time(message=m, user_id=user_id, type=type, cat=cat, day=day))
    else:
        mesg = bot.send_message(message.chat.id, "Введите текст:")
        bot.register_next_step_handler(mesg,
                                       lambda m: get_rem_text(message=m, user_id=user_id, type=type, cat=cat, day=day,
                                                              time=message.text))


def get_rem_text(message, user_id, type, cat, day, time):
    db.add_reminder(user_id=user_id, time=time, category=cat, date=day, text=message.text, type=type)
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

        if call.data == "remind":
            bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
            key = types.InlineKeyboardMarkup()
            but_1 = types.InlineKeyboardButton(text="Добавить напоминание", callback_data=call.data + "_add")
            but_2 = types.InlineKeyboardButton(text="Удалить напоминание", callback_data=call.data + "_del")
            but_3 = types.InlineKeyboardButton(text="📌 Меню", callback_data="menu")
            key.add(but_1, but_2, but_3)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="Выберите действие:",
                                  reply_markup=key)

        if call.data == "remind_add":
            bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
            key = types.InlineKeyboardMarkup()
            but_1 = types.InlineKeyboardButton(text="Каждый день", callback_data=call.data + "_0")
            but_2 = types.InlineKeyboardButton(text="Каждый месяц", callback_data=call.data + "_1")
            but_3 = types.InlineKeyboardButton(text="📌 Меню", callback_data="menu")
            key.add(but_1, but_2, but_3)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="Выберите частоту:",
                                  reply_markup=key)

        if call.data == "remind_add_0" or call.data == "remind_add_1":
            bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
            but_1 = types.InlineKeyboardButton(text="Напоминание", callback_data=call.data + "_-1")
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="Выберите категорию трат или напоминание о заполнении:",
                                  reply_markup=category_key(user_id=call.from_user.id, ex_in="ex",
                                                            callback=call.data + "_").add(but_1))

        if call.data[:len("remind_add_1_")] == "remind_add_1_" and call.data.count("_") == 3:
            bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
            mesg = bot.send_message(call.message.chat.id, "🗓️ Введите день (число от 1 до 31)")
            bot.register_next_step_handler(mesg,
                                           lambda m: get_rem_data(message=m, user_id=call.from_user.id, type=1,
                                                                  cat=call.data[
                                                                      len("remind_add_1_"):]))

        if call.data[:len("remind_add_0_")] == "remind_add_0_" and call.data.count("_") == 3:
            bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
            mesg = bot.send_message(call.message.chat.id, "🕛 Введите время в формате HH:MM:SS")
            bot.register_next_step_handler(mesg,
                                           lambda m: get_rem_time(message=m, user_id=call.from_user.id, type=0,
                                                                  cat=call.data[
                                                                      len("remind_add_0_"):]))


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

    #

    if message.text == 'add notification':
        db.add_reminder(user_id=message.chat.id, date=11, time='20:17:00', type=1, text='Срочно оплати')

    if message.text == 'delete notification':
        db.erase_reminder(notification_id=1)


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
    db.init_db(flag_drop=True)

    main()
