# DocuMind 🧠

DocuMind, PDF dosyalarından özet çıkaran ve gelecekte belge içeriğiyle sohbet etmeyi amaçlayan bir uygulamadır.

## 🔧 Kurulum

git clone https://github.com/nehirunal/documind.git
cd documind

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload


### Frontend

```bash
cd frontend
npm install
npm run dev

