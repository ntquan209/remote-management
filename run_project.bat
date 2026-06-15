@echo off
title Kich hoat He thong Remote Lab

echo --------------------------------------------------
echo [1/2] Dang khoi dong Backend (FastAPI)...
echo --------------------------------------------------
:: Mo cua so CMD moi, kich hoat venv va chay Uvicorn
start cmd /k "cd backend && .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

echo --------------------------------------------------
echo [2/2] Dang khoi dong Giao dien Frontend (Vite)...
echo --------------------------------------------------
:: Mo them mot cua so CMD nua de chay npm run dev cho Frontend
start cmd /k "cd frontend && npm run dev"

echo --------------------------------------------------
echo KICH HOAT HOAN THANH!
echo Tu dong mo Trinh duyet Web sau 3 giay...
echo --------------------------------------------------
timeout /t 3 >nul
start http://localhost:5173