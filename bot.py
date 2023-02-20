import config
import telebot
import db

bot = telebot.TeleBot(config.token)


if __name__ == '__main__':
    db.init_db()
