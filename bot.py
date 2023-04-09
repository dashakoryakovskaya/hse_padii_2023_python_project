import telebot
import config
import db
import cv2
import os

from fns import FnsAccess

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


@bot.message_handler(content_types=['photo', 'document'])
def qr_code_reader(message):
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
        bot.send_message(message.chat.id, 'Успешно!')

        client = FnsAccess()
        ticket = client.get_ticket(qr_code)

        elements = ticket["ticket"]["document"]["receipt"]["items"]
        totalItems = []
        for el in elements:
            print(el["name"] + ' ' + str((el["sum"] + 99) // 100), end='\n')
            totalItems.append(el["name"] + ' ' + str((el["sum"] + 99) // 100))  # копейки в рубли с округлением вверх
        totalSum = str((ticket["ticket"]["document"]["receipt"]["totalSum"] + 99) // 100)
        print(totalSum, end='\n')
        bot.send_message(message.chat.id, totalSum)
        client.refresh_token_function()


    except:
        bot.send_message(message.chat.id, 'Попробуйте еще раз :(')
    os.remove(file_info.file_path)  # удаление изображения с чеком после распознавания

def main():
    # TODO: добавить проверку соединения и тд
    bot.polling()


if __name__ == '__main__':
    # TODO: нужен ли тут flag_drop=True ?
    db.init_db(flag_drop=True)
    main()
