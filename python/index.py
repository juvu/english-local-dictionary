#! usr/bin/python3
# -*- coding: utf-8 -*-

__version__ = 'v0.4'
__author__ = 'seast19<sun@orzx.cn>'


import os
import sys
import re
import time
import json

import threading
import queue
import requests


class EnglishDict:
    def __init__(self):
        self.__q = queue.Queue()  # 将词库添加到此队列
        self.__q_write = queue.Queue()  # 将搜索结果添加到此

        self.__data_a = {}  # 整理后最终要保存的内容

        self.theading_num = 50  # 爬取翻译线程数

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

    def __write_file(self):
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
        print('*' * 30)
        print('开始写入json文件...')
        with open('data/data.json', 'w+', encoding='utf-8') as f:
            json.dump(self.__data_a, f)
        print('写入j结束')

    def product_tasks(self):
        """发布任务

        :return:
        """

        start_time1 = time.time()  # 开始时间

        # 从文件获取单词添加到队列
        self.__put_words_to_queue()

        # 搜索结果
        for i in range(self.theading_num):
            t = threading.Thread(target=self.__search_word)  # 创建线程
            t.start()

        # 读取结果
        t2 = threading.Thread(target=self.__write_file)
        t2.start()
        t2.join()  # 阻塞此线程

        print('耗时：%d分%.2f秒', ((time.time() - start_time1) // 60, (time.time() - start_time1) % 60))

    def user_search(self):
        """用户输入单词进行查询

        :return:
        """

        # 加载词库
        print('加载词库中...')
        try:
            with open('data/data.json', 'r', encoding='utf-8') as f:
                f2 = json.load(f)
                print('加载成功!')
                print('+============================+')

        except FileNotFoundError:
            print('无数据文件!')
            input('按回车键退出...')
            return
        except json.decoder.JSONDecodeError:
            print('数据文件不正确或已损坏!')
            input('按回车键退出...')
            return

        # 循环搜索单词
        while True:
            word = input('请输入单词(按回车键确认)：').strip()  # 用户输入字符串

            # 字符串非空检测
            if word == '':
                print('输入内容不能为空！')
                print('+----------------------------+')
                continue

            start_time = time.time()  # 计时开始
            results_list = []  # 临时保存结果

            # 将输入单词变换大小写，中文则原型
            word_list = {word, word.lower(), word.upper(), word.capitalize()}

            # 查询变形单词(英语单词)
            for i in word_list:
                # 查询单词
                if i in f2:
                    try:
                        results_list = f2[i]
                        break
                    except KeyError as e:
                        print(e)
                        print('%s  -->该单词查询出错！' % i)
                        continue

            # 找不到英语单词，则从结果反向查找(汉语)
            else:
                reg_exp = '[;: ]' + word + '[;: ]'  # 创建正则表达式

                # 查找翻译内容是否有匹配项
                for k, v in f2.items():
                    value = v[0]['v']
                    res = re.findall(reg_exp, value)
                    if res:
                        results_list.append(v[0])  # 添加匹配条目的第一条数据，后面条目数据为此key变形，无需记录

            # 输出搜索结果
            if results_list:
                print('共 %d 条数据: %.3fs\n' % (len(results_list), (time.time() - start_time)))
                for i, v in enumerate(results_list):
                    print('[%d] %-15s  ==> %s\n' % (i + 1, v['k'], v['v']))

            else:
                print('无搜索结果!')

            print('+----------------------------+')


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
          
          汉英互译词典
+============================+""")

    eng = EnglishDict()

    # 输入参数确定运行方式
    if len(sys.argv) > 1:
        flag1 = sys.argv[1]
        if flag1 == '-s':
            # 生产者
            eng.product_tasks()
        else:
            print('参数错误!  [-s]:开始爬取词库翻译')
    else:
        # 用户查询
        eng.user_search()
