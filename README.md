# DocuMind 🧠

DocuMind, PDF dosyalarından özet çıkaran ve gelecekte belge içeriğiyle sohbet etmeyi amaçlayan bir uygulamadır.

## 🔧 Kurulum

### Backend


cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload

### Frontend

cd frontend
npm install
npm run dev
