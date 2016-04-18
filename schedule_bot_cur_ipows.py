# -*- coding: utf-8 -*-

import requests
import time
import subprocess
import os

requests.packages.urllib3.disable_warnings()

INTERVAL = 2  # check interval
ADMIN_ID = 54801157  # ADMIN Unique ID
URL = 'https://api.telegram.org/bot'  # bot API address
TOKEN = '115893408:AAEE7xfAv76fPext6zBLBiLfveBTd9L2QoY'
offset = 0  # id of last update

TOKEN_DATABASE_FILE = "/root/python_telegram/users.csv"
TOKEN_DATABASE = {}


# Bot API
def check_updates():
    global offset
    data = {'offset': offset + 1, 'limit': 5, 'timeout': 0}  # request
    try:
        request = requests.post(URL + TOKEN + '/getUpdates', data=data)  # send update request
    except:
        log_event('Error getting updates')
        return False

    if not request.status_code == 200: return False  # check server answer
    if not request.json()['ok']: return False  # check api success
    for update in request.json()['result']:  # check every element in list
        offset = update['update_id']  # get message ID

        if not 'message' in update or not 'text' in update['message']:
            log_event('Unknown update: %s' % update)
            continue  # next update
        from_id = update['message']['chat']['id']  # get sender ID
        name = update['message']['chat']['first_name']  # get sender username
        #		if from_id <> ADMIN_ID:
        #			send_text("You're not authorized to use me!", from_id)
        #			log_event('Unathorized: %s' % update)
        #			continue
        message = update['message']['text']

        if from_id != ADMIN_ID:
            send_text(ADMIN_ID, u"#log_event:\n%s (%s):\n%s" % (name, from_id, message))

        parameters = (offset, name, from_id, message)
        log_event('%s (%s) >> Bot:\n%s' % (name, from_id, message))  # show ID and text in log
        run_command(*parameters)


def run_command(offset, name, from_id, cmd):
    cmd = cmd.strip()
    if cmd == '/ping':
        send_text(from_id, u'понг!')
    elif cmd == '/start' or cmd == '/help':
        send_help(from_id)
    elif cmd.find("/auth_token") != -1:
        schedule_add_token(from_id, cmd[12:len(cmd)])
    elif cmd == '/timetable_today' or cmd == '/t':
        schedule_get(from_id, "today")
    elif cmd == '/timetable_tomorrow' or cmd == '/tt':
        schedule_get(from_id, "tomorrow")
    elif cmd == '/timetable_week' or cmd == '/tw':
        schedule_get(from_id, "week")
    elif cmd.find("/search_user") != -1:
        search_user(from_id, cmd[13:len(cmd)])
    elif from_id == ADMIN_ID:
        if cmd.find('/n') != -1:
            NASTYA_ID = 419502
            send_text(NASTYA_ID, cmd[3:len(cmd)])
        if cmd.find('/b1') != -1:
            send_to_group(1, cmd[4:len(cmd)])
            send_text(ADMIN_ID, u"Текст:\n'%s' отправлен первой группе" % cmd[4:len(cmd)])
        if cmd.find('/b2') != -1:
            send_to_group(2, cmd[4:len(cmd)])
            send_text(ADMIN_ID, u"Текст:\n'%s' отправлен второй группе" % cmd[4:len(cmd)])
        if cmd.find('/message') == 0:
            command = cmd.partition(" ")[0]
            params = cmd.partition(" ")[2]
            id = params.partition(" ")[0]
            message = params.partition(" ")[2]
            if command == '/message':
                send_text(id, message)
                send_text(ADMIN_ID, u"#log_event:\nTo %s:\n%s" % (str(id), message))


def log_event(text):
    event = '== %s ==\n%s' % (time.ctime(), text.encode("utf-8"))
    print event


def send_text(chat_id, text):
    log_event('Bot >> %s:\n%s' % (chat_id, text))
    data = {'chat_id': chat_id, 'text': text}
    request = requests.post(URL + TOKEN + '/sendMessage', data=data)
    if not request.status_code == 200:
        return False
    return request.json()['ok']


def send_to_group(gid, text):
    for user, data in TOKEN_DATABASE.items():
        if data['gid'] == str(gid):
            send_text(user, text)


# IPOWS Schedule
def search_user(from_id, lname):
    if TOKEN_DATABASE.has_key(str(from_id)):
        if len(lname) == 0:
            send_text(from_id, u"Для получения информации о пользователе, введите фамилию.\n'/search_user Иванов'")
            return False
        request_data = requests.get("http://ipows.ru/api.php",
                                    {'action': 'getinfo', 'token': TOKEN_DATABASE[str(from_id)]['token'],
                                     'lname': lname})
    else:
        send_text(from_id, u"Сначала необходимо произвести аутентификацию.")
        return False
    if not request_data.status_code == 200:
        send_text(from_id, u"Ошибка при подключении к ipows.ru при попытке получить заметку.")
        return False
    persons = parse_persons_xml(request_data.text)
    send_text(from_id, persons)


def parse_persons_xml(xml_text):
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml_text.encode('utf8'))
    result_text = u""
    if root.find('result').text == 'good':
        persons = root.find('persons')
        person = persons.find('person')
        if person == None:
            return u"Такой пользователь не найден."
        for person in persons.findall('person'):
            name = person.find('fname').text + ' ' + person.find('lname').text
            phone = person.find('phone').text
            skype = person.find('skype').text
            room = person.find('hostel').text
            vk = person.find('vkid').text

            result_text += u"%s\n" % name
            if phone != None:
                result_text += u"Тел: %s\n" % phone
            if skype != None:
                result_text += u"Skype: %s\n" % skype
            if vk != None:
                result_text += u"vk: https://vk.com/id%s\n" % vk
            if room != None:
                result_text += u"Комната в общаге: %s\n\n" % room
        return result_text
    else:
        return u"Ошибка парсинга XML с сервера."


# Help
def send_help(from_id):
    text = u'Для доступа к расписанию, необходимо пройти аутентификацию при помощи команды "/auth_token TOKEN". Токен можно получить на сайте ipows.ru на личной странице.'
    text += u'\nДоступные команды:'
    text += u'\n/timetable_today (/t) - расписание на сегодня.'
    text += u'\n/timetable_tomorrow (/tt) - расписание на завтра'
    text += u'\n/timetable_week (/tw) - расписание на ближайшую неделю'
    text += u'\n/search_user Фамилия - поиск пользователя по фамилии'
    text += u'\n/auth_token Токен - авторизоваться на IPOWS API'
    text += u'\n/help - вывод этого сообщения'
    text += u'\n/ping - получить сообщение "понг" от бота'
    if from_id == ADMIN_ID:
        text += u'\n/n текст - отправить сообщение с текстом Насте'
        text += u'\n/b1 текст - отправить сообщение с текстом группе ИПОВС-11'
        text += u'\n/b2 текст - отправить сообщение с текстом группе ИПОВС-12'
        text += u'\n/message ID текст - отправить сообщение с текстом пользователю по ID'
    send_text(from_id, text)


# Schedule usage
def schedule_get(from_id, time):
    if TOKEN_DATABASE.has_key(str(from_id)):
        request_data = requests.get("http://ipows.ru/api.php",
                                    {'token': TOKEN_DATABASE[str(from_id)]['token'], 'action': 'get', 'time': time})
        if not request_data.status_code == 200:
            send_text(from_id, u"Ошибка при подключении к ipows.ru. Код ошибки: %s" % str(request_data.status_code))
            return False
        parse_schedule_xml(request_data.text, from_id)
    else:
        send_text(from_id,
                  u"Сначала необходимо произвести аутентификацию, отправив токен с помощью команды /auth_token.")


def parse_schedule_xml(xml_text, from_id):
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml_text.encode('utf8'))

    if root.find('result').text == 'good':
        result_text = u""

        if root.find('timetable') == None:
            result_text = u"Занятий нет"

        for timetable in root.findall('timetable'):
            found_first_pair = False
            result_text += u"%s (%s)\n" % (timetable.find('weekday').text, timetable.find('day').text)
            for subject in timetable.findall('subject'):
                subject_number = subject.find('number').text
                subject_timestart = subject.find('timestart').text
                subject_timefinish = subject.find('timefinish').text
                subject_name = subject.find('name').text
                subject_room = subject.find('room').text
                if subject_name != None:
                    found_first_pair = True
                    result_text += u"%s. %s - %s " % (subject_number, subject_timestart, subject_timefinish)
                    result_text += u"%s (%s)\n" % (subject_name, subject_room)
                elif found_first_pair == True:
                    result_text += u"%s. %s - %s Свободное время\n" % (
                        subject_number, subject_timestart, subject_timefinish)
            result_text += u"\n"
        send_text(from_id, result_text)
    else:
        send_text(from_id, u"Ошибка парсинга ответа от сервера.")


# Token usage		
def read_dict_from_csv(filename):
    from csv import reader
    dict = {}
    for key, value, gid in reader(open(filename)):
        dict[key] = {'token': value, 'gid': gid}
    return dict


def write_dict_to_csv(filename, dictionary):
    from csv import writer
    w = writer(open(filename, "w"))
    for key, value in dictionary.items():
        w.writerow([key, value['token'], value['gid']])


def init_token_database():
    global TOKEN_DATABASE
    TOKEN_DATABASE = read_dict_from_csv(TOKEN_DATABASE_FILE)
    if len(TOKEN_DATABASE) == 0:
        send_text(ADMIN_ID, u"#log_event:\nПроизведена попытка загрузить пустую базу данных токенов :(")


def add_token_to_database(from_id, token, group_id):
    global TOKEN_DATABASE
    TOKEN_DATABASE[str(from_id)] = {'token': str(token), 'gid': str(group_id)}


def schedule_add_token(from_id, token):
    # check token on server
    request_data = requests.get("http://ipows.ru/api.php", {'action': 'auth', 'token': token})
    if not request_data.status_code == 200:
        send_text(from_id, u"Ошибка при подключении к серверу. Код ошибки: %s" % str(request_data.status_code))
    import xml.etree.ElementTree as ET
    root = ET.fromstring(request_data.text.encode('utf8'))
    if root.find('result').text == 'good':
        group_id = root.find('gid').text
        add_token_to_database(from_id, token, group_id)
        write_dict_to_csv(TOKEN_DATABASE_FILE, TOKEN_DATABASE)
        send_text(from_id, u"Аутентификация прошла успешно.")
    else:
        send_text(from_id, u"Ошибка авторизации. Токен '%s' некорректен." % token)


# Main loop
if __name__ == "__main__":
    init_token_database()
    # schedule_add_token(ADMIN_ID, "c585f911932a80b5920185812c14fa0c")
    send_text(ADMIN_ID, u"#log_event (%s):\nСервер запущен" % time.ctime())
    while True:
        try:
            check_updates()
            time.sleep(INTERVAL)
        except KeyboardInterrupt:
            print 'Interrupted by user'
            break
        except:
            send_text(ADMIN_ID, u"Бот упал. :(")
            raise
