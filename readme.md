# 本地英语词典查询

命令行英语单词离线查询工具


* 使用[dwyl/english-words](https://github.com/dwyl/english-words)提供的词典
* 使用百度翻译接口
* 已离线所有单词翻译结果保存至本地`data/data.json`

***

**使用方法**

  
* 查询单词

    - Windows：
    
        下载[release](https://github.com/seast19/english-local-dictionary/releases)下的zip包，解压运行exe文件即可查询
    
    - linux:
    
        安装依赖后运行`index.py`
        ```    
        sudo pip install -r requirements.txt
        python3 index.py
        ```
        

* 自行爬取翻译

    ```
    python3 index.py -s
    ```
    爬取到的json文件将保存在`data/data.json`文件
  
    ```
    