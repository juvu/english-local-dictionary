package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"io/ioutil"
	"net/http"
	"net/url"
	"os"
	"regexp"
	"strings"
	"sync"
	"time"
)

//搜索结果反序列化
type SubItem struct {
	K string `json:"k"`
	V string `json:"v"`
}

//主结构体
type English struct {
	treadingNub int            //线程数
	qWords      chan string    //词库队列
	qResults    chan []SubItem //搜索结果队列

	qSearchDone   chan int             //搜索线程结束
	qSaveFileDone chan int             //写文件线程结束
	data          map[string][]SubItem //最终数据
	lock          sync.Mutex           //对data的锁
}

//工厂模式,初始化数据
func NewStruct() *English {
	c := &English{}

	c.treadingNub = 40 //爬虫线程数
	c.qWords = make(chan string, 2000)
	c.qResults = make(chan []SubItem, 200)

	c.qSearchDone = make(chan int, c.treadingNub)
	c.qSaveFileDone = make(chan int, 1)
	c.data = make(map[string][]SubItem)

	//加载json文件,若有内容则设置c.data
	_ = c.loadJsonFile()

	return c

}

//添加单词到管道
func (c *English) putWords() {
	//打开词库文件
	f, err := os.Open("data/words.txt")
	if err != nil {
		fmt.Println("打开words文件失败")
		fmt.Println(err)
		close(c.qWords)
		return
	}
	defer f.Close()

	//读取每行数据，添加到管道
	fmt.Println("开始添加词库至管道")
	rd := bufio.NewReader(f)
	for {
		//按行读取
		line, err := rd.ReadString('\n')
		if err != nil || err == io.EOF {
			close(c.qWords)
			break
		}
		//去除空白
		lineTrim := strings.TrimSpace(line)
		//搜索结果存在则跳过
		c.lock.Lock()
		_, ok := c.data[lineTrim]
		c.lock.Unlock()
		if !ok {
			c.qWords <- lineTrim
		}

	}
	fmt.Println("添加词库到管道完毕")
	fmt.Println("+==============================+")
	return
}

//从百度翻译获取单项搜索结果
func (c *English) searchWord() {
	client := &http.Client{}
	//headers
	headers := http.Header{}
	headers.Set("Content-Type", "application/x-www-form-urlencoded") //重要！无此项导致无法获取正确响应
	headers.Add("User-Agent", "Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_1 like Mac OS X) AppleWebKit/603.1.30 (KHTML, like Gecko) Version/10.0 Mobile/14E304 Safari/602.1")
	headers.Add("Referer", "https://fanyi.baidu.com/")

	for word := range c.qWords {
		//添加data
		data := url.Values{}
		data.Set("kw", word)
		data1 := strings.NewReader(data.Encode())
		req, _ := http.NewRequest("POST", "https://fanyi.baidu.com/sug", data1)
		//添加headers
		req.Header = headers

		//请求数据
		resp, err := client.Do(req)
		if err != nil {
			fmt.Println(err)
			continue
		}

		//处理数据
		body, err := ioutil.ReadAll(resp.Body)
		_ = resp.Body.Close() //因for循环，手动关闭resp.body
		if err != nil {
			fmt.Println(err)
			continue
		}

		//反序列化json
		resultStruct := struct {
			Data []SubItem `json:"data"`
		}{}
		err = json.Unmarshal(body, &resultStruct)
		if err != nil {
			fmt.Println(err)
			continue
		}
		//添加到管道
		if len(resultStruct.Data) > 0 {
			fmt.Println("添加了：", word)
			c.qResults <- resultStruct.Data
		} else {
			fmt.Println("跳过：", word)
		}

	}
	//该线程结束则给出标记
	c.qSearchDone <- 1
	fmt.Println("退出线程")

}

//保存为json文件
func (c *English) saveFile() {
	//将结果放入data
	for item := range c.qResults {
		key := item[0].K
		c.lock.Lock()
		c.data[key] = item
		c.lock.Unlock()
	}
	fmt.Println("开始写入文件")
	//反序列化map
	jsonData, err := json.Marshal(c.data)
	if err != nil {
		fmt.Println("序列化json失败")
		fmt.Println(err)
		return
	}
	//保存文件
	err = ioutil.WriteFile("data/data.json", jsonData, 0666)
	if err != nil {
		fmt.Println("保存为文件失败")
		fmt.Println(err)
		return
	}

	fmt.Println("写入文件成功")
	c.qSaveFileDone <- 1

}

//生产者
func (c *English) StartSpider() {
	//添加单词进管道
	go c.putWords()

	//多线程爬虫
	for i := 0; i < c.treadingNub; i++ {
		go c.searchWord()
	}

	//写入文件
	go c.saveFile()

	//等待爬取完毕后关闭c.qResults
	for i := 0; i < c.treadingNub; i++ {
		<-c.qSearchDone
	}
	fmt.Println("所有搜索线程结束")
	close(c.qResults)

	<-c.qSaveFileDone

}

//加载json词库
func (c *English) loadJsonFile() error {
	fmt.Printf("加载词库中...")

	//读取json文件内容
	dat, err := ioutil.ReadFile("data/data.json")
	if err != nil {
		fmt.Println("加载json文件失败")
		return err
	}

	//反序列化为map
	err = json.Unmarshal(dat, &c.data)
	if err != nil {
		fmt.Println("json反序列化失败")
		return err
	}

	fmt.Println("加载成功")
	fmt.Println("+==============================+")
	return nil
}

//用户搜索
func (c *English) UserSearch() {
	//检测json文件是否载入
	if len(c.data) == 0 {
		temp := 1
		fmt.Println("按回车键退出...")
		_, _ = fmt.Scanln(&temp)
		return
	}

	//搜索单词//
	for {
		//用户输入
		word := ""
		fmt.Printf("请输入单词（按回车键确认）：")
		_, err := fmt.Scanln(&word)
		if err != nil {
			fmt.Printf("\n输入无效！请重新输入\n")
			fmt.Println(err)
			fmt.Println("+------------------------------+")
			continue
		}
		//开始时间
		startTime := time.Now()
		//去除空白
		word = strings.TrimSpace(word)
		//单词变为大小写
		wordList := [...]string{strings.ToLower(word), strings.ToUpper(word), strings.Title(word)}

		//英文搜中文
		var resultList []SubItem //存放搜索结果结果
		ok := false
		for _, v := range wordList {
			resultList, ok = c.data[v]
			if ok {
				break
			}
		}

		//英文无结果搜索中文
		if len(resultList) == 0 {

			regExp := regexp.MustCompile("[;: ]" + wordList[0] + "[;: ]")
			for _, v2 := range c.data {
				value := v2[0].V
				flag := regExp.MatchString(value)
				if flag {
					resultList = append(resultList, v2[0])
				}
			}
		}

		//显示结果
		lastTime := time.Since(startTime) //持续搜索时间
		if len(resultList) > 0 {
			fmt.Printf("共 %d 条数据: %.3fs\n\n", len(resultList), lastTime.Seconds())
			for i3, v3 := range resultList {
				fmt.Printf("[%d] %-15s  ==> %s\n\n", i3+1, v3.K, v3.V)
			}
		} else {
			fmt.Printf("无搜索结果 %.3fs\n\n", lastTime.Seconds())
		}

		fmt.Println("+------------------------------+")
	}
}

func main() {
	fmt.Println(`
                  _ _     _      
                 | (_)   | |     
   ___ _ __   _ _| |_ ___| |__   
 / _ \ '_ \ / _' | | / __| '_ \
|  __/ | | | (_| | | \__ \ | | |
 \___|_| |_|\__, |_|_|___/_| |_|
            __/ |
           |___/
          
           汉英互译词典
+==============================+`)

	eng := NewStruct()

	//开始爬取
	//eng.StartSpider()

	//用户搜索
	eng.UserSearch()

}
