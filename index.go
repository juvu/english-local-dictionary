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

type SubItem struct {
	K string `json:"k"`
	V string `json:"v"`
}

type English struct {
	treadingNub   int                  //线程数
	q             chan string          //词库队列
	qWrite        chan []SubItem       //搜索结果队列
	qSearchDown   chan int             //线程结束
	qSaveFileDown chan int             //线程结束
	data          map[string][]SubItem //最终数据
	lock          sync.Mutex           //对data的锁
}

//工厂模式
//初始化数据
func NewStruct() *English {
	c := &English{}

	c.treadingNub = 40
	c.q = make(chan string, 2000)
	c.qWrite = make(chan []SubItem, 200)
	c.qSearchDown = make(chan int)
	c.qSaveFileDown = make(chan int)
	c.data = make(map[string][]SubItem)

	//加载json文件,若有内容则设置c.data
	_ = c.loadJsonFile()

	return c

}

//添加词库到队列
func (c *English) putWords() {
	//打开词库文件
	f, err := os.Open("data/words.txt")
	if err != nil {
		fmt.Println("打开words文件失败")
		fmt.Println(err)
		close(c.q)
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
			close(c.q)
			break
		}
		//去除空白
		lineTrim := strings.TrimSpace(line)
		//搜索结果存在则跳过
		c.lock.Lock()
		_, ok := c.data[lineTrim]
		c.lock.Unlock()
		if !ok {
			c.q <- lineTrim

		} else {
			//fmt.Println("跳过", lineTrim)
		}

	}
	fmt.Println("添加词库到管道完毕")
	fmt.Println("+==============================+")
	return
}

//从百度翻译获取结果
func (c *English) searchWord() {
	client := &http.Client{}

	headers := http.Header{}
	headers.Set("Content-Type", "application/x-www-form-urlencoded") //重要！无此项导致无法获取正确响应
	headers.Add("User-Agent", "Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_1 like Mac OS X) AppleWebKit/603.1.30 (KHTML, like Gecko) Version/10.0 Mobile/14E304 Safari/602.1")
	headers.Add("Referer", "https://fanyi.baidu.com/")

	for word := range c.q {
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
			c.qWrite <- resultStruct.Data
		} else {
			fmt.Println("跳过：", word)
		}

	}
	//该线程结束则给出标记
	c.qSearchDown <- 1
	fmt.Println("退出线程")

}

//写入文件
func (c *English) writeFile() {

	//将结果放入data
	for item := range c.qWrite {
		key := item[0].K
		c.lock.Lock()
		c.data[key] = item
		c.lock.Unlock()
	}
	//写入json文件
	fmt.Println("开始写入文件")
	jsonData, err := json.Marshal(c.data)
	if err != nil {
		fmt.Println("序列化json失败")
		fmt.Println(err)
		return
	}

	err = ioutil.WriteFile("data/data.json", jsonData, 0666)
	if err != nil {
		fmt.Println("保存为文件失败")
		fmt.Println(err)
		return
	}

	fmt.Println("写入文件成功")
	c.qSaveFileDown <- 1

}

//生产者
func (c *English) StartSearch() {
	//初始化参数
	//c.init()
	//添加单词进管道
	go c.putWords()
	//多线程爬虫
	for i := 0; i < c.treadingNub; i++ {
		go c.searchWord()
	}

	//写入文件
	go c.writeFile()

	//等待爬取完毕后关闭c.qWrite
	for i := 0; i < c.treadingNub; i++ {
		<-c.qSearchDown
	}
	fmt.Println("关闭qwrite")
	close(c.qWrite)

	<-c.qSaveFileDown

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
	//检测json问价是否载入
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
		startTime := time.Now().UnixNano()
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
		stopTime := float64(time.Now().UnixNano()-startTime) / 1000000000.0 //结束时间
		if len(resultList) > 0 {
			//fmt.Println(stopTime)
			fmt.Printf("共 %d 条数据: %.3fs\n\n", len(resultList), stopTime)
			for i3, v3 := range resultList {
				fmt.Printf("[%d] %-15s  ==> %s\n\n", i3+1, v3.K, v3.V)
			}
		} else {
			fmt.Printf("无搜索结果 %.3fs\n\n", stopTime)
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
	//eng.StartSearch()

	//用户搜索
	eng.UserSearch()

}
