# 💸 FinFlow AI

**FinFlow AI** is a modern **personal finance management web app** built with **Flask (Python)** and a clean dark-themed UI.  
It helps users **track expenses, get AI-powered insights, and receive smart financial advice & alerts**.  

---

## ✨ Features

### 🔐 Authentication
- Secure **Sign up / Login** with password hashing
- User-specific dashboards & financial records

### 📊 Expense Tracking & Dashboard
- Add, edit, and categorize expenses (Food, Travel, Entertainment, etc.)
- Interactive dashboard with charts & tables for financial visualization

### 🤖 AI Chatbot Assistant
- Natural language queries like:  
  - *“How much did I spend on food last month?”*  
  - *“Show me my top 3 categories this week”*  
- Personalized financial advice:  
  - *“You’re overspending on entertainment by 20% this month”*

### 🔮 Predictive Alerts
- Bill reminders for upcoming **rent, electricity, subscriptions**
- Cash flow prediction: warns if your balance might go negative before salary credit

### 📈 Personalized Spending Insights
- Spending pattern analysis (e.g., *“35% of food budget is spent on weekends”*)
- Monthly expense forecasting with **Prophet / LSTM**
- AI-powered **budget suggestions** based on income & spending history

### 🎨 Modern Dark-Themed UI
- Responsive, minimal, and professional dark mode design
- Grid-based layout, cards, chatbot window, and interactive charts

---

## 🛠 Tech Stack
- **Backend**: Python (Flask), SQLite (or Firebase for cloud storage)  
- **Frontend**: HTML, CSS (dark theme), JavaScript (Chart.js)  
- **AI/ML**: OpenAI API for chatbot, Time-series forecasting (Prophet/LSTM)  
- **Authentication**: Flask-Login & password hashing  

---

## 🚀 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/sufiyaanshkh/FinFlow.git
cd FinFlow

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate      # Windows

### 3. Install Dependencies
```bash
pip install -r requirements.txt

### 4. Add Environment Variables
```bash
SECRET_KEY=your_secret_key
OPENAI_API_KEY=your_openai_api_key

### 5. Run the App
```bash
cd backend
python app.py



