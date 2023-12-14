from main import app,db,User,Artist,Admin
from datetime import datetime, timedelta

twelve_hours_ago = datetime.now() - timedelta(hours=12)
one_day_ago = datetime.now() - timedelta(days=1)
one_week_ago = datetime.now() - timedelta(weeks=1)
three_weeks_ago = datetime.now() - timedelta(weeks=3)

with app.app_context():
    # db.drop_all()
    db.create_all()
    for x in range(20):
        username="User"+str(x)
        password="pass"
        email="email@"+str(x)
        if x%2==0:
            creator=False
        else:
            creator=True
            
        rem=x%5
        if rem==0:
            time=datetime.now()
        elif rem==1:
            time=one_day_ago
        elif rem==2:
            time=one_week_ago
        else:
            time=three_weeks_ago
        user=User(username=username,password=password,email=email,creator=creator,profile_picture="../static/artist.png",time=time)
        db.session.add(user)
        if creator:
            artist=Artist(username=username,profile_picture="../static/artist.png",time=time)
            db.session.add(artist)
        db.session.commit()
    db.session.add(Admin(username="ABC",password="pass"))
    db.session.commit()
