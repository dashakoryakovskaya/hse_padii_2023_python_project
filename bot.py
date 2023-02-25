import threading

import config
import telebot
import db

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
    bot.send_message(message.chat.id, "Привет ✌️ Я - бот для отслеживания твоих финансов! \n"
                                      "+sum - поступления \n"
                                      "-sum - траты \n"
                                      "user_data - информация о пользователях\n"
                                      "incomes_data - информация о поступлениях\n"
                                      "expenses_data - информация о тратах\n"
                                      "check balance - проверить баланс))")
    db.add_user(user_id=message.from_user.id, name=message.from_user.first_name)
    # bot.send_message(message.chat.id, str(threading.current_thread().ident))


@bot.message_handler(content_types=["text"])
def repeat_all_messages(message):
    # bot.send_message(message.chat.id, str(threading.current_thread().ident))
    # TODO: сделать это все через меню / кнопки, категории!!
    if message.text[0] == '+':
        db.add_money_transfer(user_id=message.from_user.id, name=message.from_user.username, date=message.date,
                       sum=int(message.text[1:]), type='', ex_in='in')
    if message.text[0] == '-':
        db.add_money_transfer(user_id=message.from_user.id, name=message.from_user.username, date=message.date,
                        sum=int(message.text[1:]), type='', ex_in='ex')
    # вся информация из таблицы по запросу имятаблицы_data
    if message.text[-4:] == 'data':
        bot.send_message(message.chat.id, message.text + ':\n' + list_of_tuples_to_str(db.sql_execute(sql="SELECT * "
                                                                                                          "FROM " +
                                                                                                          message.text[
                                                                                                          :-5])))
    if message.text == 'check balance':
        bot.send_message(message.chat.id, 'balance' + ':\n' + one_tuple_to_str(db.get_balance(user_id=message.chat.id)))

    if message.text == 'add cat':
        db.add_category(user_id=message.from_user.id, type_name='smth', ex_in='ex')

    if message.text == 'check cat':
        res = db.get_categories(user_id=message.from_user.id, ex_in='ex')
        bot.send_message(message.chat.id, str(res[0]))


def main():
    # TODO: добавить проверку соединения и тд
    bot.polling()


if __name__ == '__main__':
    # TODO: нужен ли тут flag_drop=True ?
    db.init_db(flag_drop=True)
    main()
