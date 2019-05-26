import time

import requests
import threading
import queue

import shelve

q = queue.Queue()

q_write = queue.Queue()

theading_max_num = 50
theading_now_num = 0


# 根据单词搜索结果
def searchWord():
    global theading_now_num
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_1 like Mac OS X) AppleWebKit/603.1.30 (KHTML, like Gecko) Version/10.0 Mobile/14E304 Safari/602.1',
        'Referer': 'https://fanyi.baidu.com/'
    }
    while not q.empty():
        try:
            text = q.get()
            resp = requests.post('https://fanyi.baidu.com/sug', data={'kw': text}, headers=headers)
            data = resp.json()['data']
            if len(data) == 0:
                continue
            else:
                q_write.put(resp.json()['data'])
                print('--> %s <--搜索完成' % text)
        except Exception as e:
            print(e)

    theading_now_num += 1
    print('退出线程')


# 从结果队列读取数据写入文本
def writeResults():
    global theading_now_num
    global theading_max_num

    with shelve.open('./data/data') as f:
        while theading_now_num < theading_max_num:
            text = q_write.get()
            try:
                key = text[0]['k']
                f[key] = text
                print('写入了%s' % key)
            except Exception as e:
                print(e)

    print('写入文本结束')


# 从文件获取单词添加到队列
def putWords2queue():
    start_flag = 0
    last_word = getLastWord()

    # 如果为none代表从头开始
    if not last_word:
        start_flag = 1

    with open('./data/words.txt', 'r', encoding='utf-8') as f:
        for line in f:
            word = line.strip()

            # 找到中断的点
            if start_flag == 0:
                if last_word != word:
                    continue

                start_flag = 1
                continue

            q.put(line.strip())

    print('单词加入搜索队列结束')
    print('*' * 20)


# 发布任务
def productTasks():
    global theading_max_num
    # 从文件获取单词添加到队列
    putWords2queue()

    # 搜索结果
    for i in range(theading_max_num):
        t = threading.Thread(target=searchWord)  # 创建线程
        t.start()

    # 读取结果
    t2 = threading.Thread(target=writeResults)
    t2.start()
    t2.join()


# 根据单词搜索结果
def readShelve(text):
    # print('查询 %s 结果:' % text)
    with shelve.open('./data/data') as f:
        if text in f:
            result = f.get(text)
            print('共 %d 条数据:' % len(result))
            # print('-' * 20)
            for i, v in enumerate(result):
                print(' [%d]%-15s ==> %s' % (i + 1,v['k'], v['v']))

        else:
            print('共 0 条数据')

    print('*' * 20)


# 获取shelve获取的最后一个单词
def getLastWord():
    with shelve.open('./data/data') as f:
        if len(f) == 0:
            word = None
        else:
            word = list(f)[-1]
    # print(word)
    return word


if __name__ == '__main__':
    print('欢迎使用离线英语词典！')
    print('*' * 30)

    # 生产者
    # productTasks()

    # 开始查询
    while True:
        text = input('请输入英文单词(按回车键确认)：')
        print('-' * 20)
        readShelve(text)

