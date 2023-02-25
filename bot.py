import threading

import config
import telebot
import db
from telebot import types

bot = telebot.TeleBot(config.token)


def list_of_tuples_to_str(list_tup: list):
    string = ''
    for row in list_tup:
        string += ' '.join(map(str, row)) + '\n'
    return string


def one_tuple_to_str(tup: tuple):
    return str(tup[0][0])


@bot.message_handler(commands=['start'])
def start_message(message):
    key = types.InlineKeyboardMarkup()
    but_1 = types.InlineKeyboardButton(text="Траты", callback_data="expenses")
    but_2 = types.InlineKeyboardButton(text="Поступления", callback_data="incomes")
    but_3 = types.InlineKeyboardButton(text="Статистика", callback_data="data")
    key.add(but_1, but_2, but_3)
    bot.send_message(message.chat.id, "Привет ✌️ Я - бот для отслеживания твоих финансов! \n"
                                      "user_data - информация о пользователях\n"
                                      "incomes_data - информация о поступлениях\n"
                                      "expenses_data - информация о тратах\n"
                                      "check balance - проверить баланс))", reply_markup=key)
    db.add_user(user_id=message.from_user.id, name=message.from_user.first_name)
    # bot.send_message(message.chat.id, str(threading.current_thread().ident))


# TODO: нужна /stop команда?
@bot.message_handler(commands=['stop'])
def stop(message):
    bot.send_message(message.chat.id, "До встречи!")
    bot.stop_polling()


def add_expenses_or_incomes_menu(message, user_id, name, type, date, ex_in):
    if message.text.isdigit() and int(message.text) >= 0:
        if ex_in == "ex":
            db.add_expenses(user_id=user_id, name=name, sum=int(message.text), type=type, date=date)
        else:
            db.add_incomes(user_id=user_id, name=name, sum=int(message.text), type=type, date=date)
        key = types.InlineKeyboardMarkup()
        but_1 = types.InlineKeyboardButton(text="Траты", callback_data="expenses")
        but_2 = types.InlineKeyboardButton(text="Поступления", callback_data="incomes")
        but_3 = types.InlineKeyboardButton(text="Статистика", callback_data="data")
        key.add(but_1, but_2, but_3)
        bot.send_message(message.chat.id, text="Записано!")
        bot.send_message(message.chat.id, text="Меню", reply_markup=key)
    else:
        mesg = bot.send_message(message.chat.id, "Неправильный формат :(\nВведите еще раз:")
        bot.register_next_step_handler(mesg,
                                       lambda m: add_expenses_or_incomes_menu(message=m, user_id=user_id,
                                                                              name=name,
                                                                              type=type,
                                                                              date=date, ex_in=ex_in))


# TODO: даты в расходах и доходах (пока что дата сообщения)!
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.message:
        if call.data == "menu":
            key = types.InlineKeyboardMarkup()
            but_1 = types.InlineKeyboardButton(text="Траты", callback_data="expenses")
            but_2 = types.InlineKeyboardButton(text="Поступления", callback_data="incomes")
            but_3 = types.InlineKeyboardButton(text="Статистика", callback_data="data")
            key.add(but_1, but_2, but_3)
            # bot.send_message(chat_id=call.message.chat.id, text="Меню", reply_markup=key)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Меню",
                                  reply_markup=key)
        if call.data == "expenses":
            key = types.InlineKeyboardMarkup()
            but_1 = types.InlineKeyboardButton(text="Еда", callback_data="expenses_food")
            but_2 = types.InlineKeyboardButton(text="Жилье", callback_data="expenses_house")
            but_3 = types.InlineKeyboardButton(text="Развлечения", callback_data="expenses_entertainment")
            but_4 = types.InlineKeyboardButton(text="Меню", callback_data="menu")
            key.add(but_1, but_2, but_3, but_4)
            # bot.send_message(chat_id=call.message.chat.id, text="Выберите категорию:", reply_markup=key)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="Выберите категорию:", reply_markup=key)
        if call.data[:len("expenses_")] == "expenses_":
            bot.answer_callback_query(call.id, "Ведите сумму")
            mesg = bot.send_message(call.message.chat.id, "Введите сумму")

            bot.register_next_step_handler(mesg,
                                           lambda m: add_expenses_or_incomes_menu(message=m, user_id=call.from_user.id,
                                                                                  name="",
                                                                                  type=call.data[len("expenses_"):],
                                                                                  date=mesg.date, ex_in="ex"))

        if call.data == "incomes":
            key = types.InlineKeyboardMarkup()
            but_1 = types.InlineKeyboardButton(text="Зарплата", callback_data="incomes_salary")
            but_2 = types.InlineKeyboardButton(text="Подарок", callback_data="incomes_gift")
            but_3 = types.InlineKeyboardButton(text="Меню", callback_data="menu")
            key.add(but_1, but_2, but_3)
            # bot.send_message(chat_id=call.message.chat.id, text="Выберите категорию:", reply_markup=key)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="Выберите категорию:", reply_markup=key)

        if call.data[:len("incomes_")] == "incomes_":
            bot.answer_callback_query(call.id, "Ведите сумму")
            mesg = bot.send_message(call.message.chat.id, "Введите сумму")
            bot.register_next_step_handler(mesg,
                                           lambda m: add_expenses_or_incomes_menu(message=m,
                                                                                  user_id=call.from_user.id,
                                                                                  name="",
                                                                                  type=call.data[len("incomes_"):],
                                                                                  date=mesg.date, ex_in="in"))

        if call.data == "data":
            key = types.InlineKeyboardMarkup()
            but_1 = types.InlineKeyboardButton(text="Баланс", callback_data="data_balance")
            but_2 = types.InlineKeyboardButton(text="Расходы", callback_data="data_expenses")
            but_3 = types.InlineKeyboardButton(text="Доходы", callback_data="data_incomes")
            but_4 = types.InlineKeyboardButton(text="Меню", callback_data="menu")
            key.add(but_1, but_2, but_3, but_4)
            # bot.send_message(chat_id=call.message.chat.id, text="Выберите категорию:", reply_markup=key)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="Выберите категорию:", reply_markup=key)

        if call.data == "data_balance":
            bot.send_message(call.message.chat.id, 'balance' + ':\n' + one_tuple_to_str(
                db.sql_execute(sql=f"SELECT total FROM balance WHERE user_id={call.from_user.id};")))


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
        bot.send_message(message.chat.id, 'balance' + ':\n' + one_tuple_to_str(
            db.sql_execute(sql=f"SELECT total FROM balance WHERE user_id={message.from_user.id};")))


def main():
    # TODO: добавить проверку соединения и тд
    bot.polling()


if __name__ == '__main__':
    # TODO: нужен ли тут flag_drop=True ?
    db.init_db(flag_drop=True)
    main()
