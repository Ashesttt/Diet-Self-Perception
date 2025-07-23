from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import date
import os

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True)

class Record(Base):
    __tablename__ = 'records'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    record_date = Column(Date)
    choice = Column(String(20))

engine = create_engine('sqlite:///./data.db')
Base.metadata.create_all(bind=engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI()
import os
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

@app.get('/u/{username}')
async def user_page(request: Request, username: str, db: Session = Depends(get_db)):
    # 获取或创建用户
    user = db.query(User).filter(User.username == username).first()
    if not user:
        user = User(username=username)
        db.add(user)
        db.commit()
        db.refresh(user)

    # 检查今日记录
    today = date.today()
    existing_record = db.query(Record).filter(
        Record.user_id == user.id,
        Record.record_date == today
    ).first()

    # 获取历史记录
    records = db.query(Record).filter(
        Record.user_id == user.id
    ).order_by(Record.record_date.desc()).all()

    # 计算统计数据
    total_records = db.query(Record).filter(Record.user_id == user.id).count()
    eat_much_count = db.query(Record).filter(
        Record.user_id == user.id,
        Record.choice == 'eat_much'
    ).count()
    not_eat_much_count = total_records - eat_much_count

    # 计算连续天数
    current_streak = {'eat_much': 0, 'not_eat_much': 0}
    for record in sorted(records, key=lambda x: x.record_date, reverse=True):
        if record.choice == 'eat_much':
            if current_streak['eat_much'] == 0:
                current_streak['eat_much'] += 1
            else:
                break
        else:
            if current_streak['not_eat_much'] == 0:
                current_streak['not_eat_much'] += 1
            else:
                break

    return templates.TemplateResponse('user.html', {
        'request': request,
        'user': user,
        'existing_record': existing_record,
        'records': records,
        'stats': {
            'total_days': total_records,
            'eat_much_count': eat_much_count,
            'eat_much_percent': round(eat_much_count/total_records*100, 2) if total_records else 0,
            'not_eat_much_count': not_eat_much_count,
            'not_eat_much_percent': round(not_eat_much_count/total_records*100, 2) if total_records else 0,
            'current_eat_much_streak': current_streak['eat_much'],
            'current_not_eat_much_streak': current_streak['not_eat_much']
        }
    })

@app.post('/submit')
async def submit_record(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    user = db.query(User).filter(User.username == data['username']).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    today = date.today()
    existing = db.query(Record).filter(
        Record.user_id == user.id,
        Record.record_date == today
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="今日已记录")

    new_record = Record(
        user_id=user.id,
        record_date=today,
        choice=data['choice']
    )
    db.add(new_record)
    db.commit()
    return {"status": "success"}