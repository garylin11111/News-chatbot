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
    url = "https://www.ettoday.net/news/hot-news.htm"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")
    news_items = soup.select("div.piece.clearfix")
    count = 0

    for item in news_items:
        a_tag = item.find("a", class_="pic")
        if not a_tag:
            continue

        title = a_tag.get("title", "").strip()
        link = a_tag.get("href", "").strip()
        img_tag = a_tag.find("img")
        time_tag = item.find("span", class_="date")

        img_url = ""
        if img_tag:
            img_url = img_tag.get("data-original") or img_tag.get("src", "")
            if img_url.startswith("//"):
                img_url = "https:" + img_url

        if link.startswith("//"):
            link = "https:" + link
        elif link.startswith("/"):
            link = "https://www.ettoday.net" + link

        pub_time = time_tag.text.strip() if time_tag else ""

        if title and link:
            doc_ref = db.collection("熱門新聞").document(title)
            doc_ref.set({
                "title": title,
                "link": link,
                "image": img_url,
                "time": pub_time
            })
            count += 1

    return f"已成功寫入 {count} 筆熱門新聞到 Firebase。"


@app.route("/webhook", methods=["POST"])
def webhook():
    req = request.get_json(force=True)
    action = req.get("queryResult", {}).get("action")

    if action == "getTechNews":
        keyword = req.get("queryResult", {}).get("parameters", {}).get("news_topic", "")
        docs = db.collection("科技新聞").get()
        result = ""

        for doc in docs:
            data = doc.to_dict()
            if keyword in data["title"]:
                result += f"● {data['title']}\n👉 {data['link']}\n\n"

        if not result:
            result = f"找不到與「{keyword}」有關的新聞，請試試其他關鍵字。"

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