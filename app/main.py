from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Date, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import date, timedelta
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

    # 计算连续打卡天数（无论吃多还是没吃多）
    consecutive_days = 0
    if records:
        sorted_records = sorted(records, key=lambda x: x.record_date, reverse=True)
        prev_date = sorted_records[0].record_date
        consecutive_days = 1
        for record in sorted_records[1:]:
            if (prev_date - record.record_date).days == 1:
                consecutive_days += 1
                prev_date = record.record_date
            else:
                break

    # 获取今日饮食记录
    today = date.today()
    today_food_record = db.query(FoodRecord).filter(
        FoodRecord.user_id == user.id,
        FoodRecord.record_date == today
    ).first()

    # 计算各餐平均摄入量
    food_records = db.query(FoodRecord).filter(FoodRecord.user_id == user.id).all()
    breakfast_total = sum(fr.breakfast for fr in food_records if fr.breakfast > 0)
    lunch_total = sum(fr.lunch for fr in food_records if fr.lunch > 0)
    dinner_total = sum(fr.dinner for fr in food_records if fr.dinner > 0)
    snack_total = sum(fr.snack for fr in food_records if fr.snack > 0)
    
    breakfast_days = sum(1 for fr in food_records if fr.breakfast > 0)
    lunch_days = sum(1 for fr in food_records if fr.lunch > 0)
    dinner_days = sum(1 for fr in food_records if fr.dinner > 0)
    snack_days = sum(1 for fr in food_records if fr.snack > 0)

    avg_breakfast_calories = round(breakfast_total / breakfast_days, 1) if breakfast_days else 0
    avg_lunch_calories = round(lunch_total / lunch_days, 1) if lunch_days else 0
    avg_dinner_calories = round(dinner_total / dinner_days, 1) if dinner_days else 0
    avg_snack_calories = round(snack_total / snack_days, 1) if snack_days else 0

    # 计算平均每日摄入热量和热量缺口
    total_calories = sum(fr.total_calories for fr in food_records if fr.total_calories)
    food_days = len([fr for fr in food_records if fr.total_calories])
    avg_daily_calories = round(total_calories / food_days, 1) if food_days > 0 else 0

    return templates.TemplateResponse('user.html', {
        'request': request,
        'user': user,
        'existing_record': existing_record,
        'records': records,
        'today_food_record': today_food_record,
        'stats': {
            'total_days': total_records,
            'eat_much_count': eat_much_count,
            'eat_much_percent': round(eat_much_count / total_records * 100, 1) if total_records > 0 else 0,
            'not_eat_much_count': not_eat_much_count,
            'not_eat_much_percent': round(not_eat_much_count / total_records * 100, 1) if total_records > 0 else 0,
            'consecutive_days': consecutive_days,
            'avg_calorie_deficit': round(user.bmr - avg_daily_calories, 1) if user.bmr and avg_daily_calories else 0,
            'avg_breakfast_calories': avg_breakfast_calories,
            'avg_lunch_calories': avg_lunch_calories,
            'avg_dinner_calories': avg_dinner_calories,
            'avg_snack_calories': avg_snack_calories
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

@app.get('/u/{username}/charts')
async def charts_page(request: Request, username: str, db: Session = Depends(get_db)):
    # 获取用户
    user = db.query(User).filter(User.username == username).first()
    if not user:
        user = User(username=username)
        db.add(user)
        db.commit()
        db.refresh(user)

    # 获取最近30天的数据
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)

    # 获取食物记录
    food_records = db.query(FoodRecord).filter(
        FoodRecord.user_id == user.id,
        FoodRecord.record_date >= thirty_days_ago
    ).order_by(FoodRecord.record_date).all()

    # 获取饮食选择记录
    record_choices = db.query(Record).filter(
        Record.user_id == user.id,
        Record.record_date >= thirty_days_ago
    ).order_by(Record.record_date).all()

    # 准备图表数据
    dates = []
    calories = []
    calorie_deficit = []
    eat_much = []
    not_eat_much = []
    streaks = []

    # 初始化日期范围
    current_date = thirty_days_ago
    date_to_calories = {}
    date_to_choice = {}

    # 填充食物记录数据
    for record in food_records:
        date_str = record.record_date.strftime('%Y-%m-%d')
        date_to_calories[date_str] = record.total_calories
        if user.bmr:
            date_to_calories[f'{date_str}_deficit'] = user.bmr - record.total_calories

    # 填充饮食选择数据
    for record in record_choices:
        date_str = record.record_date.strftime('%Y-%m-%d')
        date_to_choice[date_str] = record.choice

    # 计算连续打卡天数
    consecutive_days = 0
    prev_date = None

    # 生成日期序列和对应数据
    while current_date <= today:
        date_str = current_date.strftime('%Y-%m-%d')
        dates.append(date_str)

        # 热量数据
        calories.append(date_to_calories.get(date_str, 0))

        # 热量缺口数据
        deficit = date_to_calories.get(f'{date_str}_deficit', 0) if user.bmr else 0
        calorie_deficit.append(deficit)

        # 饮食选择数据
        eat_much.append(1 if date_to_choice.get(date_str) == 'eat_much' else 0)
        not_eat_much.append(1 if date_to_choice.get(date_str) == 'not_eat_much' else 0)

        # 连续打卡天数
        if date_str in date_to_choice:
            if prev_date and (current_date - prev_date).days == 1:
                consecutive_days += 1
            else:
                consecutive_days = 1
            prev_date = current_date
        else:
            consecutive_days = 0
        streaks.append(consecutive_days)

        current_date += timedelta(days=1)

    # 各餐热量占比
    breakfast_total = sum(fr.breakfast for fr in food_records if fr.breakfast)
    lunch_total = sum(fr.lunch for fr in food_records if fr.lunch)
    dinner_total = sum(fr.dinner for fr in food_records if fr.dinner)
    snack_total = sum(fr.snack for fr in food_records if fr.snack)
    total = breakfast_total + lunch_total + dinner_total + snack_total

    meals = {
        'breakfast': breakfast_total,
        'lunch': lunch_total,
        'dinner': dinner_total,
        'snack': snack_total
    }

    # 饮食规律热力图数据 (按星期)
    weekday_patterns = {
        'breakfast': [0, 0, 0, 0, 0, 0, 0],  # 周日到周六
        'lunch': [0, 0, 0, 0, 0, 0, 0],
        'dinner': [0, 0, 0, 0, 0, 0, 0],
        'snack': [0, 0, 0, 0, 0, 0, 0],
        'count': [0, 0, 0, 0, 0, 0, 0]
    }

    for record in food_records:
        weekday = record.record_date.weekday()  # 0=周一, 6=周日
        # 转换为周日=0, 周六=6
        adjusted_weekday = (weekday + 1) % 7
        weekday_patterns['count'][adjusted_weekday] += 1
        weekday_patterns['breakfast'][adjusted_weekday] += record.breakfast or 0
        weekday_patterns['lunch'][adjusted_weekday] += record.lunch or 0
        weekday_patterns['dinner'][adjusted_weekday] += record.dinner or 0
        weekday_patterns['snack'][adjusted_weekday] += record.snack or 0

    # 计算平均值
    eating_patterns = {
        'breakfast': [],
        'lunch': [],
        'dinner': [],
        'snack': []
    }

    for i in range(7):
        count = weekday_patterns['count'][i] or 1
        eating_patterns['breakfast'].append(round(weekday_patterns['breakfast'][i] / count, 1))
        eating_patterns['lunch'].append(round(weekday_patterns['lunch'][i] / count, 1))
        eating_patterns['dinner'].append(round(weekday_patterns['dinner'][i] / count, 1))
        eating_patterns['snack'].append(round(weekday_patterns['snack'][i] / count, 1))

    # 饮食习惯数据
    eating_habits = {
        'eat_much': eat_much,
        'not_eat_much': not_eat_much
    }

    return templates.TemplateResponse('charts.html', {
        'request': request,
        'user': user,
        'dates': dates,
        'calories': calories,
        'meals': meals,
        'eating_habits': eating_habits,
        'calorie_deficit': calorie_deficit,
        'eating_patterns': eating_patterns,
        'streaks': streaks
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

@app.get('/u/{username}/history')
async def user_history(request: Request, username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 获取所有历史记录
    records = db.query(Record).filter(
        Record.user_id == user.id
    ).order_by(Record.record_date.desc()).all()

    # 获取所有食物记录并按日期存储
    food_records = db.query(FoodRecord).filter(
        FoodRecord.user_id == user.id
    ).all()
    food_record_map = {fr.record_date: fr for fr in food_records}

    # 合并记录数据
    for record in records:
        food_record = food_record_map.get(record.record_date)
        if food_record:
            record.breakfast_calories = food_record.breakfast
            record.lunch_calories = food_record.lunch
            record.dinner_calories = food_record.dinner
            record.snack_calories = food_record.snack
            record.total_calories = food_record.total_calories
            # 计算热量缺口（BMR - 总卡路里）
            if user.bmr:
                record.calorie_deficit = user.bmr - food_record.total_calories
            else:
                record.calorie_deficit = 0
        else:
            record.breakfast_calories = 0
            record.lunch_calories = 0
            record.dinner_calories = 0
            record.snack_calories = 0
            record.total_calories = 0
            record.calorie_deficit = 0

    return templates.TemplateResponse('history.html', {
        'request': request,
        'user': user,
        'records': records
    })

@app.get('/u/{username}/statistics')
async def user_statistics(request: Request, username: str, db: Session = Depends(get_db)):
    # 获取用户
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 获取历史记录
    records = db.query(Record).filter(
        Record.user_id == user.id
    ).order_by(Record.record_date.desc()).all()

    # 获取饮食记录
    food_records = db.query(FoodRecord).filter(
        FoodRecord.user_id == user.id
    ).all()

    # 计算原有统计数据
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

    # 计算最长连续记录
    max_streak = {'eat_much': 0, 'not_eat_much': 0}
    current_eat_much = 0
    current_not_eat_much = 0
    for record in sorted(records, key=lambda x: x.record_date):
        if record.choice == 'eat_much':
            current_eat_much += 1
            current_not_eat_much = 0
            max_streak['eat_much'] = max(max_streak['eat_much'], current_eat_much)
        else:
            current_not_eat_much += 1
            current_eat_much = 0
            max_streak['not_eat_much'] = max(max_streak['not_eat_much'], current_not_eat_much)

    # 计算平均每周记录次数
    if total_records > 0 and records:
        first_record_date = min(records, key=lambda x: x.record_date).record_date
        days_since_first_record = (date.today() - first_record_date).days
        weeks = days_since_first_record / 7
        avg_weekly_records = round(total_records / weeks, 1) if weeks > 0 else total_records
    else:
        avg_weekly_records = 0

    # 计算饮食平均摄入量
    breakfast_total = sum(fr.breakfast for fr in food_records if fr.breakfast > 0)
    lunch_total = sum(fr.lunch for fr in food_records if fr.lunch > 0)
    dinner_total = sum(fr.dinner for fr in food_records if fr.dinner > 0)
    snack_total = sum(fr.snack for fr in food_records if fr.snack > 0)
    
    breakfast_days = sum(1 for fr in food_records if fr.breakfast > 0)
    lunch_days = sum(1 for fr in food_records if fr.lunch > 0)
    dinner_days = sum(1 for fr in food_records if fr.dinner > 0)
    snack_days = sum(1 for fr in food_records if fr.snack > 0)

    
    avg_breakfast_calories = round(breakfast_total / breakfast_days, 1) if breakfast_days else 0
    avg_lunch_calories = round(lunch_total / lunch_days, 1) if lunch_days else 0
    avg_dinner_calories = round(dinner_total / dinner_days, 1) if dinner_days else 0
    avg_snack_calories = round(snack_total / snack_days, 1) if snack_days else 0

    breakfast_total = sum(fr.breakfast for fr in food_records if fr.breakfast > 0)
    lunch_total = sum(fr.lunch for fr in food_records if fr.lunch > 0)
    dinner_total = sum(fr.dinner for fr in food_records if fr.dinner > 0)
    snack_total = sum(fr.snack for fr in food_records if fr.snack > 0)
    
    breakfast_days = sum(1 for fr in food_records if fr.breakfast > 0)
    lunch_days = sum(1 for fr in food_records if fr.lunch > 0)
    dinner_days = sum(1 for fr in food_records if fr.dinner > 0)
    snack_days = sum(1 for fr in food_records if fr.snack > 0)
    
    avg_breakfast_calories = round(breakfast_total / breakfast_days, 1) if breakfast_days else 0
    avg_lunch_calories = round(lunch_total / lunch_days, 1) if lunch_days else 0
    avg_dinner_calories = round(dinner_total / dinner_days, 1) if dinner_days else 0
    avg_snack_calories = round(snack_total / snack_days, 1) if snack_days else 0

    # 计算热量缺口相关指标
    if user.bmr and food_records:
        total_deficit = 0
        qualified_count = 0
        for fr in food_records:
            deficit = user.bmr - fr.total_calories
            total_deficit += deficit
            if 0 < deficit <= 500:  # 假设合理的热量缺口为0-500大卡
                qualified_count += 1
        
        avg_calorie_deficit = round(total_deficit / len(food_records), 1)
        calorie_deficit_rate = round(qualified_count / len(food_records) * 100, 2) if food_records else 0
        
        # 计算累计消耗脂肪
        total_calorie_deficit = round(total_deficit, 1)
        # 1公斤脂肪约等于7700千卡，1斤(500克)约等于3850千卡
        total_fat_lost_kg = round(total_calorie_deficit / 7700, 4) if total_calorie_deficit > 0 else 0
    else:
        avg_calorie_deficit = 0
        calorie_deficit_rate = 0
        total_calorie_deficit = 0
        total_fat_lost_kg = 0

    # 计算连续打卡天数
    current_streak_days = 0
    if records:
        sorted_dates = sorted(set(r.record_date for r in records), reverse=True)
        today = date.today()
        if sorted_dates[0] == today:
            current_streak_days += 1
            for i in range(1, len(sorted_dates)):
                if (sorted_dates[i-1] - sorted_dates[i]).days == 1:
                    current_streak_days += 1
                else:
                    break

    return templates.TemplateResponse('statistics.html', {
        'request': request,
        'user': user,
        'stats': {
            'total_days': total_records,
            'eat_much_count': eat_much_count,
            'eat_much_percent': round(eat_much_count/total_records*100, 2) if total_records else 0,
            'not_eat_much_count': not_eat_much_count,
            'not_eat_much_percent': round(not_eat_much_count/total_records*100, 2) if total_records else 0,
            'current_eat_much_streak': current_streak['eat_much'],
            'current_not_eat_much_streak': current_streak['not_eat_much'],
            'max_eat_much_streak': max_streak['eat_much'],
            'max_not_eat_much_streak': max_streak['not_eat_much'],
            'avg_weekly_records': avg_weekly_records,
            'avg_breakfast_calories': avg_breakfast_calories,
            'avg_lunch_calories': avg_lunch_calories,
            'avg_dinner_calories': avg_dinner_calories,
            'avg_snack_calories': avg_snack_calories,
            'avg_calorie_deficit': avg_calorie_deficit,
            'total_calorie_deficit': total_calorie_deficit,
            'total_fat_lost_kg': total_fat_lost_kg,
            'current_streak': current_streak_days,
            'calorie_deficit_rate': calorie_deficit_rate
        }
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
