import json

import requests

HOST = 'irkkt-mobile.nalog.ru:8888'
DEVICE_OS = 'iOS'
CLIENT_VERSION = '2.9.0'
DEVICE_ID = '7C82010F-16CC-446B-8F66-FC4080C66521'
ACCEPT = '*/*'
USER_AGENT = 'billchecker/2.9.0 (iPhone; iOS 13.6; Scale/2.00)'
ACCEPT_LANGUAGE = 'ru-RU;q=1, en-US;q=0.9'
CLIENT_SECRET = 'IyvrAbKt9h/8p6a7QPh8gpkXYQ4='
OS = 'Android'
headers = {
        'Host': HOST,
        'Accept': ACCEPT,
        'Device-OS': DEVICE_OS,
        'Device-Id': DEVICE_ID,
        'clientVersion': CLIENT_VERSION,
        'Accept-Language': ACCEPT_LANGUAGE,
        'User-Agent': USER_AGENT,
    }


class FnsAccess:
    HOST = 'irkkt-mobile.nalog.ru:8888'
    DEVICE_OS = 'iOS'
    CLIENT_VERSION = '2.9.0'
    DEVICE_ID = '7C82010F-16CC-446B-8F66-FC4080C66521'
    ACCEPT = '*/*'
    USER_AGENT = 'billchecker/2.9.0 (iPhone; iOS 13.6; Scale/2.00)'
    ACCEPT_LANGUAGE = 'ru-RU;q=1, en-US;q=0.9'
    CLIENT_SECRET = 'IyvrAbKt9h/8p6a7QPh8gpkXYQ4='
    OS = 'Android'

    def __init__(self, chat_id, phone, code, session_id, refresh_token):
        self.__session_id = None
        self.__phone = phone
        self.__code = code
        self.__chat_id = chat_id
        self.__session_id = session_id
        self.__refresh_token = refresh_token

    def refresh_token_function(self) -> None:
        url = f'https://{self.HOST}/v2/mobile/users/refresh'
        payload = {
            'refresh_token': self.__refresh_token,
            'client_secret': self.CLIENT_SECRET
        }

        resp = requests.post(url, json=payload, headers=headers)

        self.__session_id = resp.json()['sessionId']
        self.__refresh_token = resp.json()['refresh_token']

    def _get_ticket_id(self, qr: str) -> str:
        """
        Get ticker id by info from qr code
        :param qr: text from qr code. Example "t=20200727T174700&s=746.00&fn=9285000100206366&i=34929&fp=3951774668&n=1"
        :return: Ticket id. Example "5f3bc6b953d5cb4f4e43a06c"
        """
        url = f'https://{self.HOST}/v2/ticket'
        payload = {'qr': qr}
        headers = {
            'Host': self.HOST,
            'Accept': self.ACCEPT,
            'Device-OS': self.DEVICE_OS,
            'Device-Id': self.DEVICE_ID,
            'clientVersion': self.CLIENT_VERSION,
            'Accept-Language': self.ACCEPT_LANGUAGE,
            'sessionId': self.__session_id,
            'User-Agent': self.USER_AGENT,
        }

        resp = requests.post(url, json=payload, headers=headers)

        return resp.json()["id"]

    def get_ticket(self, qr: str) -> dict:
        """
        Get JSON ticket
        :param qr: text from qr code. Example "t=20200727T174700&s=746.00&fn=9285000100206366&i=34929&fp=3951774668&n=1"
        :return: JSON ticket
        """
        ticket_id = self._get_ticket_id(qr)
        url = f'https://{self.HOST}/v2/tickets/{ticket_id}'
        headers = {
            'Host': self.HOST,
            'sessionId': self.__session_id,
            'Device-OS': self.DEVICE_OS,
            'clientVersion': self.CLIENT_VERSION,
            'Device-Id': self.DEVICE_ID,
            'Accept': self.ACCEPT,
            'User-Agent': self.USER_AGENT,
            'Accept-Language': self.ACCEPT_LANGUAGE,
            'Content-Type': 'application/json'
        }

        resp = requests.get(url, headers=headers)

        return resp.json()


'''if __name__ == '__main__':
    client = FnsAccess()
    qr_code = "t=20230318T1501&s=229.98&fn=9960440502975708&i=13772&fp=4215413791&n=1"  # test receipt
    ticket = client.get_ticket(qr_code)
    # print(json.dumps(ticket, indent=4, ensure_ascii=False))

    elements = ticket["ticket"]["document"]["receipt"]["items"]
    totalItems = []
    for el in elements:
        totalItems.append(el["name"] + ' ' + str((el["sum"] + 99) // 100))  # копейки в рубли с округлением вверх
    for item in totalItems:
        print(item, end='\n')
    totalSum = str((ticket["ticket"]["document"]["receipt"]["totalSum"] + 99) // 100)
    print(totalSum, end='\n')

    # client.refresh_token_function() '''
