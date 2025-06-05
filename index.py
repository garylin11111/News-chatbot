import requests
from bs4 import BeautifulSoup

import json

import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, render_template, request, make_response, jsonify
from datetime import datetime, timedelta, timezone

import os
import google.generativeai as genai

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time

app = Flask(__name__)

cred = credentials.Certificate("newschatbotkey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

@app.route("/")
def index():
    return render_template('index.html')

    
@app.route("/news")
def news():
    count = 0
    headers = {"User-Agent": "Mozilla/5.0"}

    url_et = "https://www.ettoday.net/news/focus/AI%E7%A7%91%E6%8A%80/"
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

        now = datetime.now()
        try:
            pub_dt = datetime.strptime(pub_time, "%m/%d %H:%M")
            pub_dt = pub_dt.replace(year=now.year)
            if pub_dt > now:
                pub_dt = pub_dt.replace(year=now.year - 1)
            timestamp = pub_dt.replace(tzinfo=timezone.utc)
        except:
            match = re.match(r"(\d+)(分鐘|小時)前", pub_time)
            if match:
                amount = int(match.group(1))
                unit = match.group(2)
                if unit == "分鐘":
                    timestamp = datetime.now(timezone.utc) - timedelta(minutes=amount)
                elif unit == "小時":
                    timestamp = datetime.now(timezone.utc) - timedelta(hours=amount)
                else:
                    timestamp = datetime.now(timezone.utc)
            else:
                timestamp = datetime.now(timezone.utc)

        db.collection("科技新聞總表").add({
            "title": title,
            "link": link,
            "image": img_url,
            "source": "ETtoday",
            "time": pub_time,
            "timestamp": timestamp
        })
        count += 1

    print(f"寫入第 {count} 筆：{title}")


@app.route("/DispNews", methods=["GET", "POST"])
def DispNews():
    if request.method == "POST":
        keyword = request.form["NewsKeyword"].lower().strip()
        docs = db.collection("科技新聞總表")\
                 .order_by("timestamp", direction=firestore.Query.DESCENDING)\
                 .get()

        info = ""
        for item in docs:
            data = item.to_dict()
            title = data.get("title", "").lower()

            if keyword in title:
                timestamp = data.get("timestamp")
                if isinstance(timestamp, datetime):
                    now = datetime.now(timezone.utc)
                    diff = now - timestamp
                    minutes_ago = int(diff.total_seconds() / 60)
                    if minutes_ago < 60:
                        time_info = f"{minutes_ago} 分鐘前"
                    elif minutes_ago < 1440:
                        hours_ago = minutes_ago // 60
                        time_info = f"{hours_ago} 小時前"
                    else:
                        time_info = timestamp.astimezone().strftime('%Y-%m-%d %H:%M')
                else:
                    time_info = data.get("time", "無時間資訊")

                info += f"<b>標題：</b><a href='{data.get('link', '#')}' target='_blank'>{data.get('title')}</a><br>"
                info += f"<b>來源：</b>{data.get('source', '未知')}<br>"
                info += f"<b>時間：</b>{time_info}<br>"
                if data.get("image"):
                    info += f"<img src='{data['image']}' width='300'><br>"
                info += "<hr>"

        if not info:
            info = "❌ 沒有找到符合關鍵字的新聞。"
        return info

    else:
        return render_template("news.html")

@app.route("/webhook", methods=["POST"])
def webhook():
    req = request.get_json(force=True)
    action = req.get("queryResult", {}).get("action")

    if action == "getTechNews":
        keyword_raw = req.get("queryResult", {}).get("parameters", {}).get("any", "").lower().strip()
        keyword_clean = keyword_raw.replace("新聞", "").replace("消息", "").strip()

        keyword_mapping = {
            "nvidia": "輝達",
            "jensen huang": "黃仁勳",
            "chatgpt": "chatgpt",
            "google": "google",
            "openai": "openai",
            "tsmc": "台積電",
            "ai": "ai"
        }
        keyword = keyword_mapping.get(keyword_clean, keyword_clean)

        info = f"我是科技新聞聊天機器人，您要查詢的新聞是: {keyword}\n\n"

        docs = db.collection("科技新聞總表").get()
        result = ""

        for doc in docs:
            data = doc.to_dict()
            title = data.get("title", "").lower()
            if keyword in title:
                result += f"● {data['title']} ({data.get('source', '未知')})\n"
                result += f"👉 {data['link']}\n"
                if data.get("time"):
                    result += f"🕒 發佈時間：{data['time']}\n"
                result += "\n"

        if not result:
            result = "❌ 很抱歉，找不到與這個關鍵字相關的新聞內容。"

        return make_response(jsonify({"fulfillmentText": info + result}))

    elif action == "getJobInfo":
        job_keyword = req.get("queryResult", {}).get("parameters", {}).get("job_keyword", "").strip()
        info = f"🔍 關鍵字：{job_keyword}\n\n"

        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")

            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )

            url = f"https://www.104.com.tw/jobs/search/?keyword={job_keyword}"
            driver.get(url)
            time.sleep(5)

            job_cards = driver.find_elements(By.CSS_SELECTOR, "article.b-block--top-bord")

            count = 0
            for card in job_cards:
                try:
                    title_elem = card.find_element(By.CSS_SELECTOR, 'a.js-job-link')
                    title = title_elem.text.strip()
                    link = title_elem.get_attribute('href').split("?")[0]  # 只保留主要網址

                    company_elem = card.find_element(By.CSS_SELECTOR, 'a[href*="company"]')
                    company = company_elem.text.strip()

                    detail_elems = card.find_elements(By.CSS_SELECTOR, 'ul.b-list-inline__items li')
                    details = "、".join([d.text for d in detail_elems]) if detail_elems else ""

                    info += f"● {title}（公司：{company}）\n📍 {details}\n👉 {link}\n\n"
                    count += 1
                    if count >= 3:
                        break
                except Exception:
                    continue

            if count == 0:
                info += "❌ 找不到符合的職缺，請換個關鍵字試試看。"

            driver.quit()

        except Exception as e:
            info = f"⚠️ 發生錯誤：{str(e)}"

        return make_response(jsonify({"fulfillmentText": info}))

    elif action == "getStockInfo":
        stock_input = req.get("queryResult").get("parameters").get("stock_no", "").strip()

        stock_mapping = {
            "台積電": "2330",
            "鴻海": "2317",
            "聯發科": "2454",
            "聯電": "2303",
            "中華電信": "2412",
            "大立光": "3008",
            "長榮": "2603",
            "陽明": "2609",
            "萬海": "2615",
            "中鋼": "2002"
        }

        stock_no = stock_mapping.get(stock_input, stock_input) 

        today = datetime.now()
        date_str = today.strftime("%Y%m01")
        url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date_str}&stockNo={stock_no}"

        try:
            Data = requests.get(url)
            result = json.loads(Data.text)

            if result.get("stat") == "OK" and result.get("data"):
                latest = result["data"][-1] 
                date = latest[0]
                close_price = latest[6]
                volume = latest[1]
                open_price = latest[3]

                info = f"📈 股票代號：{stock_no}（查詢關鍵字：{stock_input}）\n"
                info += f"📅 最近交易日：{date}\n"
                info += f"💰 收盤價：{close_price} 元，開盤價：{open_price} 元\n"
                info += f"📊 成交股數：{volume} 股"
            else:
                info = f"❌ 查無股票「{stock_input}」的資料，請確認股票代號或名稱是否正確。"

        except Exception as e:
            info = f"⚠️ 無法取得股票資料，錯誤訊息：{str(e)}"

        return make_response(jsonify({"fulfillmentText": info}))



    elif action == "input.unknown":
        info = req["queryResult"]["queryText"]
        genai.configure(api_key='AIzaSyC_E5AIrjA55e2lOtHFOnBYVbNL1q7nn_w')
        model = genai.GenerativeModel('gemini-2.0-flash',generation_config={"max_output_tokens": 128})
        response = model.generate_content(info)
        info = response.text

        return make_response(jsonify({"fulfillmentText": info}))

    return make_response(jsonify({"fulfillmentText": "⚠️ 目前無法處理這個請求"}))


@app.route("/AI")
def AI():
    genai.configure(api_key = 'AIzaSyC_E5AIrjA55e2lOtHFOnBYVbNL1q7nn_w')
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content('我想查詢靜宜大學資管系的評價？')
    return response.text



if __name__ == "__main__":
    app.run(debug=True)
