#! usr/bin/python3
# -*- coding: utf-8 -*-
import copy
import time

import requests
import threading
import queue

import shelve

q = queue.Queue()
q_write = queue.Queue()
q_stop = queue.Queue()

theading_max_num = 30


# 从百度搜索获取单词结果
def searchWord():
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_1 like Mac OS X) AppleWebKit/603.1.30 (KHTML, like Gecko) Version/10.0 Mobile/14E304 Safari/602.1',
        'Referer': 'https://fanyi.baidu.com/'
    }
    # print(q.empty())
    while not q.empty():
        try:
            text = q.get()
            resp = requests.post('https://fanyi.baidu.com/sug', data={'kw': text}, headers=headers)
            data = resp.json()['data']
            if len(data) == 0:
                continue
            else:
                q_write.put(resp.json()['data'])
                print('%s -->搜索完成' % text)
        except Exception as e:
            print(e)

    q_stop.put(1)
    print('退出线程')


# 获取shelve获取的最后一个单词
def getLastWord():
    with shelve.open('./data/data') as f:
        if len(f) == 0:
            word = None
        else:
            word = list(f)[-1]

    return word


# 添加单词到队列
def putWords2queue():
    start_flag = 0
    last_word = getLastWord()
    # print(last_word)
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
                # print(last_word)
                continue

            q.put(line.strip())
            # print(q.qsize())

    print('单词加入搜索队列结束')
    print('*' * 20)


# 从结果队列读取数据写入shelve
def writeResults():
    # global theading_max_num

    with shelve.open('./data/data') as f:
        while not q.empty() or not q_write.empty():
            try:
                text = q_write.get(timeout=5)
                key = text[0]['k']
                f[key] = text
                print('%s -->写入成功' % key)
            except queue.Empty:
                break
            except Exception as e:
                print(e)
                continue

    print('写入文本结束')


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


###################################################


# 用户输入搜索信息
def start_search():
    print('加载词库中...', end='')
    with shelve.open('./data/data', 'r') as f2:
        print('ok')
        print('-' * 30)

        # 查找单词结果
        def search_result(text):
            if text in f2:
                try:
                    result = f2.get(text)
                except:
                    print('该单词查询出错！')
                    result = []
                return result
            else:
                return []

        while True:
            text0 = str(input('请输入英文单词(按回车键确认)：'))  # 原字符串
            print('-' * 30)
            start_time = time.time()

            # 将输入单词变换大小写
            text_list = [text0, text0.lower(), text0.upper(), text0.capitalize()]

            # 查询变形单词
            for i in text_list:
                res = search_result(i)
                if len(res) > 0:
                    print('共 %d 条数据: %fs' % (len(res), (time.time() - start_time)))
                    for i, v in enumerate(res):
                        print('[%d] %-15s  ==> %s\n' % (i + 1, v['k'], v['v']))
                    print('*' * 30)
                    break

            else:

                print('搜索不到该单词！')
                print('*' * 30)


if __name__ == '__main__':
    print(r"""
                  _ _     _      
                 | (_)   | |     
   ___ _ __   _ _| |_ ___| |__   
 / _ \ '_ \ / _` | | / __| '_ \  
|  __/ | | | (_| | | \__ \ | | | 
 \___|_| |_|\__, |_|_|___/_| |_| 
             __/ |               
            |___/                
 """)

    print('*' * 30)

    # 生产者
    # productTasks()

    # 开始查询
    start_search()
