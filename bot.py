import threading

import config
import telebot
import db
import cv2
import os

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
                                      "check balance - проверить баланс\n"
                                      "qr code - считать qr code")
    db.add_user(user_id=message.from_user.id, name=message.from_user.first_name)
    # bot.send_message(message.chat.id, str(threading.current_thread().ident))


@bot.message_handler(content_types=["text"])
def repeat_all_messages(message):  # TODO: поменять название функции))
    # bot.send_message(message.chat.id, str(threading.current_thread().ident))
    # TODO: сделать это все через меню / кнопки, категории!!
    if message.text[0] == '+':
        db.add_incomes(user_id=message.from_user.id, name=message.from_user.username, date=message.date,
                       sum=int(message.text[1:]), type='')
    if message.text[0] == '-':
        db.add_expenses(user_id=message.from_user.id, name=message.from_user.username, date=message.date,
                        sum=int(message.text[1:]), type='')
    # вся информация из таблицы по запросу имятаблицы_data
    if message.text[-4:] == 'data':
        bot.send_message(message.chat.id, message.text + ':\n' + list_of_tuples_to_str(db.sql_execute(sql="SELECT * "
                                                                                                          "FROM " +
                                                                                                          message.text[
                                                                                                          :-5])))
    if message.text == 'check balance':
        bot.send_message(message.chat.id, 'balance' + ':\n' + one_tuple_to_str(
            db.sql_execute(sql=f"SELECT total FROM balance WHERE user_id={message.from_user.id};")))
    if message.text[0:2] == 'qr':
        bot.send_message(message.chat.id,
                         'Отправь мне фотографию qr кода')  # TODO: добавить отправление не картинкой, а файлом
        bot.register_next_step_handler(message, qr_code_reader)


@bot.message_handler(content_types=['photo'])  # TODO: удается только один раз отправить qr, дальше вылетает
def qr_code_reader(
        message):  # TODO: (если были неуспешные попытки - то можно отправлять до первой успешной, дальше вылетает)
    file_info = bot.get_file(message.photo[
                                 len(message.photo) - 1].file_id)  # TODO: также получается просто прислать qr код сразу после start, без педварительного вызова команды *qr*
    downloaded_file = bot.download_file(file_info.file_path)  # TODO: плохо это, или хорошо - хз
    src = file_info.file_path

    with open(src, 'wb') as new_file:
        new_file.write(downloaded_file)

    # bot.send_photo(message.chat.id, open(src, 'rb')) присылает отправленное фото в ответ, было просто для проверки
    try:
        img_qr = cv2.imread(src)
        detector = cv2.QRCodeDetector()
        data, bbox, clear_qr = detector.detectAndDecode(img_qr)
        bot.send_message(message.chat.id, data)
    except:
        bot.send_message(message.chat.id, 'Попробуйте еще раз, не удалось распознать qr код :(')
    os.remove(file_info.file_path)  # удаление изображения с чеком после распознавания


def main():
    # TODO: добавить проверку соединения и тд
    bot.polling()


if __name__ == '__main__':
    # TODO: нужен ли тут flag_drop=True ?
    db.init_db(flag_drop=True)
    main()
