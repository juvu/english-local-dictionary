#! usr/bin/python3
# -*- coding: utf-8 -*-
import sys
import time
import json

import threading
import queue
import requests


class EnglishDict:
    def __init__(self):
        self.__q = queue.Queue()  # 将词库添加到此队列
        self.__q_write = queue.Queue()  # 将搜索结果添加到此
        # self.q_stop = queue.Queue()

        self.__data_a = {}  # 整理后最终要保存的内容

        self.theading_num = 5  # 爬取翻译线程数

    def __put_words_to_queue(self):
        """添加单词到待搜索队列

        :return:
        """
        start_flag = 0  # 0表示有中断的点，1表示可以开始添加单词到队列

        # 获取最后一个单词
        try:
            with open('data/data.json', 'r', encoding='utf-8') as f:
                temp = json.load(f)

                # 打开成功则将原内容添加到data_a
                self.__data_a = temp

                last_word = list(temp.keys())[-1]  # 获取最后一个键
                print('上次中断点', last_word)
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            print('无历史文件')
            start_flag = 1
        print(start_flag)

        # 打开词库，添加到队列
        with open('data/words.txt', 'r', encoding='utf-8') as f2:
            for line in f2:
                word = line.strip()
                # 找到中断的点，则在下一次循环中开始添加单词到队列
                if start_flag == 0:
                    if last_word == word:
                        start_flag = 1
                    continue

                self.__q.put(word)

        print('单词加入搜索队列结束')
        print('*' * 20)

    def __search_word(self):
        """从百度翻译获取结果

        :return:
        """

        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_1 like Mac OS X) AppleWebKit/603.1.30 (KHTML, like Gecko) Version/10.0 Mobile/14E304 Safari/602.1',
            'Referer': 'https://fanyi.baidu.com/'
        }

        # 本线程循环搜索翻译，单词队列为空时退出
        while not self.__q.empty():
            try:
                word = self.__q.get()
                resp = requests.post('https://fanyi.baidu.com/sug', data={'kw': word}, headers=headers)
                data = resp.json()['data']
                if len(data) == 0:
                    print('%s -->无内容' % word)
                    continue
                else:
                    self.__q_write.put(data)
                    print('%s -->搜索完成' % word)
            except Exception as e:
                print(e)
                # raise

        # self.q_stop.put(1)
        print('退出线程')

    def __write_results(self):
        """从结果队列读取数据写入json

        :return:
        """

        # 获取爬好的数据添加到临时字典
        while True:
            try:
                item = self.__q_write.get(timeout=8)
                key = item[0]['k']
                self.__data_a.update({str(key): item})
                print('%s -->写入成功' % key)
            except queue.Empty:
                print('内容缓存完成')
                break
            except Exception as e:
                print(e)
                raise
                continue

        # 将临时字典写入json文件
        print('开始写入json文件')
        # print(self.__data_a)
        # self.__data_a.update({'oook':[{'v':'11','v':'22'}]})
        with open('data/data.json', 'w+', encoding='utf-8') as f:
            json.dump(self.__data_a, f)
        print('写入json文件结束')

    def product_tasks(self):
        """发布任务

        :return:
        """

        # 从文件获取单词添加到队列
        self.__put_words_to_queue()

        # 搜索结果
        for i in range(self.theading_num):
            t = threading.Thread(target=self.__search_word)  # 创建线程
            t.start()

        # 读取结果
        t2 = threading.Thread(target=self.__write_results)
        t2.start()
        t2.join()

    def start_search(self):
        """用户输入单词进行查询

        :return:
        """

        print('加载词库中...')
        try:
            with open('data/data.json', 'r', encoding='utf-8') as f:
                f2 = json.load(f)

                print('加载成功!')
                print('*' * 30)

                # 循环搜索单词
                while True:
                    word = str(input('请输入英文单词(按回车键确认)：'))  # 原字符串
                    start_time = time.time()  # 计时开始

                    # 将输入单词变换大小写
                    text_list = [word, word.lower(), word.upper(), word.capitalize()]

                    # 查询变形单词
                    for i in text_list:
                        if i in f2:
                            try:
                                res = f2.get(i)
                            except:
                                print('%s  -->该单词查询出错！' % i)
                                res = []
                        else:
                            res = []

                        if len(res) > 0:
                            print('共 %d 条数据: %fs' % (len(res), (time.time() - start_time)))
                            # 显示条目下的信息
                            for j, v in enumerate(res):
                                print('[%d] %-15s  ==> %s\n' % (j + 1, v['k'], v['v']))
                            print('*' * 30)
                            break
                    else:
                        print('搜索不到该单词！')
                        print('*' * 30)

        except (FileNotFoundError, json.decoder.JSONDecodeError):
            print('无数据文件或文件不正确!')
            input('按回车键退出...')


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
******************************""")

    eng = EnglishDict()

    if len(sys.argv) > 1:
        flag1 = sys.argv[1]
        if flag1 == '-s':
            # 生产者
            eng.product_tasks()
        else:
            print('参数错误!  [-s]:开始爬取词库翻译')
    else:
        # 用户查询
        eng.start_search()

    # 生产者
    # eng.product_tasks()

    # 用户查询
    # eng.start_search()
