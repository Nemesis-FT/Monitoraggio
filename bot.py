import telepot
from telepot.loop import MessageLoop

chiavi = open("telegramkey.txt", 'r')
output = chiavi.readlines()
telegram_token = output[0]


def handle(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    print(chat_id)


bot = telepot.Bot(telegram_token)
bot.getMe()
MessageLoop(bot, handle).run_as_thread()
while True:
    pass
