# 本地汉英互译词典

命令行离线汉英单词互译查询工具


* 使用[dwyl/english-words](https://github.com/dwyl/english-words)提供的词典
* 使用百度翻译接口
* 已离线所有单词翻译结果保存至本地`data/data.json`
* 支持`英语->汉语`，`汉语->英语`
* 限制于百度翻译，部分生僻单词无法搜索到

* 使用go语言重写，停止维护原python版本


***

**使用方法**

  
* 查询单词

    - Windows：
    
        下载[release](https://github.com/seast19/english-local-dictionary/releases)下的zip包，解压运行exe文件即可查询
    
    - linux:
    
        ```    
        go run index.go
        ```
        


  
   
    