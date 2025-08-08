from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Date, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import date
import os

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True)
    weight = Column(Integer)
    height = Column(Integer)
    age = Column(Integer)
    gender = Column(String(10))
    bmr = Column(Float)

class FoodRecord(Base):
    __tablename__ = 'food_records'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    record_date = Column(Date)
    breakfast = Column(Integer)
    lunch = Column(Integer)
    dinner = Column(Integer)
    snack = Column(Integer)
    total_calories = Column(Integer)

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

@app.get('/u/{username}/setting')
async def user_setting(request: Request, username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        user = User(username=username)
        db.add(user)
        db.commit()
        db.refresh(user)
    return templates.TemplateResponse('setting.html', {'request': request, 'user': user})

@app.post('/u/{username}/setting')
async def submit_setting(request: Request, username: str, db: Session = Depends(get_db)):
    data = await request.form()
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.weight = int(data.get('weight', 0))
    user.height = int(data.get('height', 0))
    user.age = int(data.get('age', 0))
    user.gender = data.get('gender', 'male')

    # 计算BMR
    if user.gender == 'male':
        user.bmr = 13.397 * user.weight + 4.799 * user.height - 5.677 * user.age + 88.362
    else:
        user.bmr = 9.247 * user.weight + 3.098 * user.height - 4.330 * user.age + 447.593

    db.commit()
    return templates.TemplateResponse('setting.html', {
        'request': request, 
        'user': user, 
        'message': '设置已保存，您的基础代谢率为: {:.2f} kcal/天'.format(user.bmr)
    })

@app.get('/u/{username}/detail')
async def food_detail(request: Request, username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    today = date.today()
    existing_record = db.query(FoodRecord).filter(
        FoodRecord.user_id == user.id,
        FoodRecord.record_date == today
    ).first()

    return templates.TemplateResponse('detail.html', {
        'request': request, 
        'user': user,
        'existing_record': existing_record
    })

@app.post('/u/{username}/detail')
async def submit_detail(request: Request, username: str, db: Session = Depends(get_db)):
    data = await request.form()
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    today = date.today()
    existing = db.query(FoodRecord).filter(
        FoodRecord.user_id == user.id,
        FoodRecord.record_date == today
    ).first()

    if existing:
        db.delete(existing)
        db.commit()

    breakfast = int(data.get('breakfast', 0))
    lunch = int(data.get('lunch', 0))
    dinner = int(data.get('dinner', 0))
    snack = int(data.get('snack', 0))
    total = breakfast + lunch + dinner + snack

    new_record = FoodRecord(
        user_id=user.id,
        record_date=today,
        breakfast=breakfast,
        lunch=lunch,
        dinner=dinner,
        snack=snack,
        total_calories=total
    )
    db.add(new_record)
    db.commit()

    # 计算热量缺口/赤字
    if not user.bmr:
        message = '请先设置您的个人资料以获取热量分析'
    else:
        difference = user.bmr - total
        if difference > 500:
            message = '热量缺口过大（{:.2f}大卡），建议科学减肥，不要过度节食'.format(difference)
        elif difference > 0:
            message = '辛苦您的努力，坚持坚持！今日热量缺口为{:.2f}大卡'.format(difference)
        elif difference > -500:
            message = '今天多吃了一点呢，明天一定少吃一点哦！今日热量盈余为{:.2f}大卡'.format(-difference)
        else:
            message = '今天吃了很多东西哦，可不能天天这么吃，如果是放纵餐那就没事了。今日热量盈余为{:.2f}大卡'.format(-difference)

    return templates.TemplateResponse('detail.html', {
        'request': request, 
        'user': user,
        'existing_record': new_record,
        'message': message
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