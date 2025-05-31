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
    homepage += "<a href='/DispNews'>查詢科技新聞</a><br>"    


    homepage += '<script src="https://www.gstatic.com/dialogflow-console/fast/messenger/bootstrap.js?v=1">'
    homepage += '</script><df-messengerintent="WELCOME"chat-title="林政彥" '
    homepage += 'agent-id="095d9a8b-87f0-48b6-9d86-97f40bb73458" '
    homepage += 'language-code="zh-tw" ></df-messenger> '


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
        keyword = req.get("queryResult", {}).get("parameters", {}).get("any", "").lower().strip()
        info = "我是科技新聞聊天機器人，您要查詢的新聞是: " + keyword + "\n\n"

        docs = db.collection("科技新聞總表").get()
        found = False

        for doc in docs:
            data = doc.to_dict()
            title = data.get("title", "").lower()
            if keyword in title:
                found = True
                info += f"● {data['title']} ({data.get('source', '未知')})\n"
                info += f"👉 {data['link']}\n"
                if data.get("time"):
                    info += f"🕒 發佈時間：{data['time']}\n"
                info += "\n"

        if not found:
            info += "❌ 很抱歉，找不到與這個關鍵字相關的新聞內容。"

        return make_response(jsonify({"fulfillmentText": info}))

    elif action == "input.unknown":
        info = req["queryResult"]["queryText"]
        api_key = os.getenv("API_KEY")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash', generation_config={"max_output_tokens": 128})
        response = model.generate_content(info)
        reply = response.text

        return make_response(jsonify({"fulfillmentText": reply}))

    return make_response(jsonify({"fulfillmentText": "⚠️ 目前無法處理這個請求"}))


@app.route("/DispNews", methods=["GET", "POST"])
def DispNews():
    if request.method == "POST":
        keyword = request.form["NewsKeyword"].lower()
        db = firestore.client()
        docs = db.collection("科技新聞總表").get()
        info = ""

        for item in docs:
            data = item.to_dict()
            title = data.get("title", "").lower()

            if keyword in title:
                info += f"<b>標題：</b><a href='{data.get('link', '#')}' target='_blank'>{data.get('title')}</a><br>"
                info += f"<b>來源：</b>{data.get('source', '未知')}<br>"
                info += f"<b>時間：</b>{data.get('time', '無時間資訊')}<br>"
                if data.get("image"):
                    info += f"<img src='{data['image']}' width='300'><br>"
                info += "<hr>"

        if not info:
            info = "❌ 沒有找到符合關鍵字的新聞。"

        return info

    else:
        return render_template("news.html")  


if __name__ == "__main__":
    app.run(debug=True)