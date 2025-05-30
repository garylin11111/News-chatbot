import requests
from bs4 import BeautifulSoup

import json

import firebase_admin
from firebase_admin import credentials, firestore
cred = credentials.Certificate("newschatbotkey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

from flask import Flask,render_template, request, make_response, jsonify,json
from datetime import datetime, timezone, timedelta

import os
import google.generativeai as genai

app = Flask(__name__)
@app.route("/")
def index():
    homepage = "<h2>科技新聞聊天機器人</h2>"
    homepage += "<a href='/news'>爬取科技新聞並存入Firebase</a><br>"
    return homepage



@app.route("/news")
def news():
    count = 0

    url_et = "https://www.ettoday.net/news/focus/AI%E7%A7%91%E6%8A%80/"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url_et, headers=headers)
    r.encoding = "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")
    et_news = soup.select("a.pic")

    for tag in et_news:
        title = tag.get("title", "").strip()
        link = tag.get("href", "").strip()
        img_tag = tag.find("img")
        img_url = img_tag.get("data-original") or img_tag.get("src") if img_tag else ""
        if img_url.startswith("//"):
            img_url = "https:" + img_url
        if link.startswith("//"):
            link = "https:" + link
        elif link.startswith("/"):
            link = "https://www.ettoday.net" + link

        parent = tag.find_parent("div", class_="piece")
        time_tag = parent.find("span", class_="date") if parent else None
        pub_time = time_tag.text.strip() if time_tag else ""

        db.collection("科技新聞總表").add({
		    "title": title,
		    "link": link,
		    "image": img_url,
		    "source": "ETtoday",
		    "time": pub_time
		})
        count += 1

    url_technews = "https://technews.tw/"
    r2 = requests.get(url_technews, headers=headers)
    r2.encoding = "utf-8"
    soup2 = BeautifulSoup(r2.text, "html.parser")
    tech_news = soup2.select("header.entry-header h1.entry-title a")

    for tag in tech_news[:20]:  
        title = tag.text.strip()
        link = tag.get("href", "").strip()
        db.collection("科技新聞總表").add({
		    "title": title,
		    "link": link,
		    "image": img_url,
		    "source": "TechNews",
		    "time": pub_time
		})
        count += 1

    url_ltn = "https://3c.ltn.com.tw/"
    r3 = requests.get(url_ltn, headers=headers)
    r3.encoding = "utf-8"
    soup3 = BeautifulSoup(r3.text, "html.parser")
    ltn_news = soup3.select("ul.list li a")

    for tag in ltn_news[:20]: 
        title = tag.text.strip()
        link = tag.get("href", "").strip()
        if link.startswith("/"):
            link = "https://3c.ltn.com.tw" + link
        db.collection("科技新聞總表").add({
		    "title": title,
		    "link": link,
		    "image": img_url,
		    "source": "自由時報 3C",
		    "time": pub_time
		})
        count += 1

    return f"共寫入 {count} 筆科技新聞（多來源）到 Firebase。"


@app.route("/webhook", methods=["POST"])
def webhook():
    req = request.get_json(force=True)
    action = req.get("queryResult", {}).get("action")

    if action == "getTechNews":
    	keyword = req.get("queryResult", {}).get("parameters", {}).get("news_topic", "").lower().strip()
	    docs = db.collection("科技新聞總表").get()
	    result = ""

    for doc in docs:
        data = doc.to_dict()
        title = data.get("title", "").lower().strip()
        if keyword in title:
            result += f"● {data['title']} ({data.get('source', '')})\n👉 {data['link']}\n\n"

    if not result:
        result = f"❌ 找不到與「{keyword}」有關的新聞，請試試其他關鍵字。"

        return make_response(jsonify({"fulfillmentText": result}))


    elif action == "input.unknown":
    	user_input = req["queryResult"]["queryText"]
    	api_key = os.getenv("API_KEY")
    	genai.configure(api_key=api_key)
    	model = genai.GenerativeModel('gemini-2.0-flash')
    	response = model.generate_content(user_input)
    	reply = response.text

    	return make_response(jsonify({"fulfillmentText": reply}))

    return make_response(jsonify({"fulfillmentText": "目前無法處理此請求"}))

if __name__ == "__main__":
    app.run(debug=True)