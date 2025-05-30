import requests
from bs4 import BeautifulSoup

import json

import firebase_admin
from firebase_admin import credentials, firestore
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

from flask import Flask,render_template, request, make_response, jsonify,json
from datetime import datetime, timezone, timedelta

import os
import google.generativeai as genai

app = Flask(__name__)

@app.route("/")
def index():
	homepage +="<br><a href=/read>讀取Firestore資料</a><br>"
	homepage +="<br><a href=/spider>爬取開眼即將上映電影,存到資料庫</a><br>"
	homepage +="<br><a href=/DispMovie>查詢電影</a><br>"
	homepage +="<br><a href=/traffic>查詢肇事路口</a><br>"
	homepage +="<br><a href=/rate>爬取開眼即將上映電影(含分級與更新日期)</a><br>"

	homepage +='<script src="https://www.gstatic.com/dialogflow-console/fast/messenger/bootstrap.js?v=1"> '
	homepage +='</script> <df-messenger intent="WELCOME" chat-title="林政彥" '
	homepage +='agent-id="095d9a8b-87f0-48b6-9d86-97f40bb73458" '
	homepage +='language-code="zh-tw"></df-messenger> '

	return homepage




@app.route("/read")
def read():
	Result=""
	db=firestore.client()
	collection_ref=db.collection("靜宜資管")
	docs=collection_ref.get()
	for doc in docs:
		Result+="文件內容:{}".format(doc.to_dict())+"<br>"
	return Result


@app.route("/spider")
def spider():
	db=firestore.client()
	url = "http://www.atmovies.com.tw/movie/next/"
	Data = requests.get(url)
	Data.encoding="utf-8"

	sp = BeautifulSoup(Data.text, "html.parser")
	result=sp.select(".filmListAllX li")

	for item in result:
		img = item.find("img")
		# print("片名",img.get("alt"))
		# print("海報",img.get("src"))
		a = item.find("a")
		# print("介紹:", "http://www.atmovies.com.tw" + a.get("href"))
		# print("編號:", a.get("href")[7:19])
		div = item.find(class_="runtime")
		#print("日期:",div.text[5:15])

		if div.text.find("片長：")>0:
			FilmLen = div.text[21:]
			#print("片長:", div.text[21:])
		else:
			FilmLen = "無"
			#print("目前無片長資訊")

		doc = {
			"title": img.get("alt"),
			"hyperlink" : "http://www.atmovies.com.tw" + a.get("href"),
			"picture": img.get("src"),
			"showDate": div.text[5:15],
			"showlength": FilmLen
		}
		
		doc_ref = db.collection("林政彥").document(a.get("href")[7:19])
		doc_ref.set(doc)
	return "資料庫已更新"

@app.route("/DispMovie", methods=["GET", "POST"])
def DispMovie():
	if request.method == "POST":
		keyword = request.form["MovieKeyword"]
		db=firestore.client()
		docs = db.collection("林政彥").order_by("showDate").get()
		info = ""

		for item in docs:
			if keyword in item.to_dict()["title"]:
				info+= "片名:<a href=" + item.to_dict()["hyperlink"] + ">" + item.to_dict()["title"] + "</a><br>"
				info+= "介紹:" + item.to_dict()["hyperlink"]+"<br>"
				info+= "海報:<img src=" + item.to_dict()["picture"]+"> </img> <br>"
				info+= "片長:" + item.to_dict()["showlength"]+"<br>"
				info+= "上映日期:" + item.to_dict()["showDate"]+"<br>"
		return info

	else:
	    return render_template("movie.html")


@app.route("/traffic", methods=["POST", "GET"])
def traffic():
    if request.method == "POST":
        keyword = request.form.get("keyword", "")  
        info = ""

        try:
            url = "https://drive.google.com/uc?export=download&id=15-IPdUxbevdipKoW8aCsSzylZ7zuak-z"
            response = requests.get(url)
            json_data = json.loads(response.text)

            for item in json_data:
                if keyword in item["路口名稱"]:
                    info += f"路口名稱：{item['路口名稱']}<br>"
                    info += f"總件數：{item['總件數']}<br>"
                    info += f"主要肇因：{item['主要肇因']}<br><br>"

            if not info:
                info = "找不到符合的路口名稱資料。"

        except Exception as e:
            info = f"讀取資料發生錯誤：{e}"

        return info

    else:
        return render_template("input1.html")

@app.route("/rate")
def rate():
    url = "https://technews.tw/"
    Data = requests.get(url)
    Data.encoding = "utf-8"
    sp = BeautifulSoup(Data.text, "html.parser")
    result=sp.select(".filmListAllX li")
    lastUpdate = sp.find(class_="smaller09").text[5:]

    for x in result:
        picture = x.find("img").get("src").replace(" ", "")
        title = x.find("img").get("alt")    
        movie_id = x.find("div", class_="filmtitle").find("a").get("href").replace("/", "").replace("movie", "")
        hyperlink = "http://www.atmovies.com.tw" + x.find("a").get("href")

        t = x.find(class_="runtime").text
        showDate = t[5:15]

        showLength = ""
        if "片長" in t:
            t1 = t.find("片長")
            t2 = t.find("分")
            showLength = t[t1+3:t2]

        r = x.find(class_="runtime").find("img")
        rate = ""
        if r != None:
            rr = r.get("src").replace("/images/cer_", "").replace(".gif", "")
            if rr == "G":
                rate = "普遍級"
            elif rr == "P":
                rate = "保護級"
            elif rr == "F2":
                rate = "輔12級"
            elif rr == "F5":
                rate = "輔15級"
            else:
                rate = "限制級"

        doc = {
            "title": title,
            "picture": picture,
            "hyperlink": hyperlink,
            "showDate": showDate,
            "showLength": showLength,
            "rate": rate,
            "lastUpdate": lastUpdate
        }

        db = firestore.client()
        doc_ref = db.collection("電影含分級").document(movie_id)
        doc_ref.set(doc)
    return "近期上映電影已爬蟲及存檔完畢，網站最近更新日期為：" + lastUpdate


@app.route("/webhook", methods=["POST"])
def webhook():
	# build a request object
    req = request.get_json(force=True)
    # fetch queryResult from json
    action =  req.get("queryResult").get("action")
    # msg =  req.get("queryResult").get("queryText")
    # info = "動作：" + action + "； 查詢內容：" + msg
    if (action == "rateChoice"):
	    rate =  req.get("queryResult").get("parameters").get("rate")
	    info = "您選擇的電影分級是：" + rate 
	    db = firestore.client()
	    collection_ref = db.collection("電影含分級")
	    docs = collection_ref.get()
	    result = ""
	    for doc in docs:
		    dict = doc.to_dict()
		    if rate in dict["rate"]:
			    result += "片名：" + dict["title"] + "\n"
			    result += "介紹：" + dict["hyperlink"] + "\n\n"
	    if result == "":
		    result = ", 抱歉資料庫目前此分級的電影"
	    else:
		    result = ", 相關電影:" + result
	    info += result


    elif (action == "MovieDetail"):
	    filmq =  req.get("queryResult").get("parameters").get("filmq")
	    any =  req.get("queryResult").get("parameters").get("any")
	    info = "您要查詢電影的" + filmq + "問題，關鍵字是" + any
	    if (filmq == "片名"):
	    	db = firestore.client()
	    	collection_ref = db.collection("電影含分級")
	    	docs = collection_ref.get()
	    	found = False
	    	for doc in docs:
	    		dict = doc.to_dict()
	    		if any in dict["title"]:
	    			found = True 
	    			info += "片名：" + dict["title"] + "\n"
	    			info += "海報：" + dict["picture"] + "\n"
	    			info += "影片介紹：" + dict["hyperlink"] + "\n"
	    			info += "片長：" + dict["showLength"] + " 分鐘\n"
	    			info += "分級：" + dict["rate"] + "\n" 
	    			info += "上映日期：" + dict["showDate"] + "\n\n"
	    	if not found:
	    		info += "很抱歉，目前無符合這個關鍵字的相關電影喔"
    elif (action == "CityWeather"):
        city =  req.get("queryResult").get("parameters").get("city")
        token = "rdec-key-123-45678-011121314"
        url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization=" + token + "&format=JSON&locationName=" + str(city)
        Data = requests.get(url)
        Weather = json.loads(Data.text)["records"]["location"][0]["weatherElement"][0]["time"][0]["parameter"]["parameterName"]
        Rain = json.loads(Data.text)["records"]["location"][0]["weatherElement"][1]["time"][0]["parameter"]["parameterName"]
        MinT = json.loads(Data.text)["records"]["location"][0]["weatherElement"][2]["time"][0]["parameter"]["parameterName"]
        MaxT = json.loads(Data.text)["records"]["location"][0]["weatherElement"][4]["time"][0]["parameter"]["parameterName"]
        info = city + "的天氣是" + Weather + "，降雨機率：" + Rain + "%"
        info += "，溫度：" + MinT + "-" + MaxT + "度"


    elif (action == "input.unknown"):
        info =  req["queryResult"]["queryText"]
        api_key = os.getenv("API_KEY")
        genai.configure(api_key = api_key)
        model = genai.GenerativeModel('gemini-2.0-flash', generation_config = {"max_output_tokens": 128})
        response = model.generate_content(info)
        info =  response.text


    return make_response(jsonify({"fulfillmentText":"我是林政彥聊天機器人,"+ info}))


@app.route("/AI")
def AI():
	# api_key = "AIzaSyCToKgX7PrvUPWtMZsShLpF5VyYYjQUJSw"
	api_key = os.getenv("API_KEY")
	genai.configure(api_key = api_key)
	model = genai.GenerativeModel('gemini-2.0-flash')
	response = model.generate_content('我想查詢靜宜大學資管系的評價？')
	return response.text

if __name__ == "__main__":
    app.run(debug=True)