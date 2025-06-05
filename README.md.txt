# News Chatbot 🔍📰

一個使用 Flask 建立的新聞聊天機器人，可串接 Firebase，並支援 Dialogflow 對話平台。此專案可提供即時新聞、天氣、股票等互動式回覆，並支援 LINE rich message 快捷鍵選單。


## 📦 專案內容

- **Flask 應用程式**：處理 webhook 與對話邏輯
- **Firebase**：作為後端資料儲存服務
- **Dialogflow**：自然語言處理與 intent 辨識
- **ETtoday 新聞爬蟲**：定期爬取 AI 科技新聞
- **天氣 / 股票 快速回覆**：支援 LINE 按鈕式 UI
- **Vercel 支援**：可部署於 vercel


📌 功能特色
🔍 自動爬取 ETtoday 科技新聞
📈 支援 Dialogflow 股票查詢意圖
🌤️ 快速回覆按鈕：台中天氣、台北天氣、高雄天氣
🧠 可擴充自然語言 intent 和 webhook 對話處理


### 1. 安裝相依套件

```bash
pip install -r requirements.txt


### 2. 設定 Firebase 金鑰
將 newschatbotkey.json 放在專案根目錄，並在 index.py 中正確引用。


### 3. 執行應用程式
```bash
python index.py
啟動後會在 http://localhost:5000/ 提供 webhook API。


### 4. 前往 http://localhost:5000/news 可測試新聞爬蟲功能。
📂 專案結構
```csharp
News-chatbot-main/
├── index.py                  # 主程式
├── newschatbotkey.json       # Firebase 認證金鑰
├── requirements.txt          # 相依套件
├── vercel.json               # Vercel 部署設定
├── static/                   # 靜態圖片檔
├── templates/                # HTML 模板


### 5. 部署到 Vercel
專案已包含 vercel.json，可直接部署至 Vercel

```bash
vercel deploy