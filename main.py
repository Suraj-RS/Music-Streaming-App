from flask import Flask, flash, redirect, render_template, request, url_for, session, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime, timedelta
from sqlalchemy import desc, func

'''
Flask application for a music streaming platoform.

Initialization : Lines 11-17
Models: Lines 19-100
Utility functions: Lines 111-156
Controllers: Lines 162-763
Controllers-Users- Lines 162-406
Controllers-Artists- Lines 407-607
Controllers-Backend Lines 608-690
Controllers-Admin Lines 691-763

'''
#Initialization

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///music_app.db"
db = SQLAlchemy(app)

#Models

class User(db.Model):
  username = db.Column(db.String(80),
                       unique=True,
                       nullable=False,
                       primary_key=True)
  email = db.Column(db.String(120), unique=True, nullable=False)
  password = db.Column(db.String(120), nullable=False)
  creator = db.Column(db.Boolean, default=False, nullable=False)
  profile_picture = db.Column(db.String(120))
  artist = db.relationship("Artist",
                           backref="user",
                           uselist=False,
                           cascade="all, delete-orphan")
  playlist = db.relationship("Playlist",
                           backref="user",
                           uselist=False,
                           cascade="all, delete-orphan")
  time = db.Column(db.DateTime)

#table for one to many relationship between playlist and songs
playlist_song =db.Table(
    'playlist_song',
    db.Column('playlist_id', db.Integer, db.ForeignKey('playlist.id')),
    db.Column('song_id', db.Integer, db.ForeignKey('song.id')))


class Playlist(db.Model):
  id = db.Column(db.Integer, primary_key=True, autoincrement=True)
  name = db.Column(db.String(255))
  username = db.Column(db.String(80), db.ForeignKey('user.username'))
  songs = db.relationship('Song', secondary='playlist_song')
  playlist_picture = db.Column(db.String(120))


class Artist(db.Model):
  username = db.Column(db.String(80),
                       db.ForeignKey('user.username'),
                       primary_key=True)
  profile_picture = db.Column(db.String(120))
  time = db.Column(db.DateTime)
  albums = db.relationship("Album",
                           backref="artist",
                           uselist=False,
                           cascade="all, delete-orphan")


class Album(db.Model):
  id = db.Column(db.Integer, primary_key=True, autoincrement=True)
  name = db.Column(db.String(255))
  artist_name = db.Column(db.String(80), db.ForeignKey('artist.username'))
  album_picture = db.Column(db.String(120))
  time = db.Column(db.DateTime)
  songs = db.relationship('Song',
                          backref='album',
                          cascade='all, delete-orphan')


class Song(db.Model):
  id = db.Column(db.Integer, primary_key=True, autoincrement=True)
  name = db.Column(db.String(255))
  artist_name = db.Column(db.String(80), db.ForeignKey('artist.username'))
  album_id = db.Column(db.Integer, db.ForeignKey('album.id'))
  path = db.Column(db.String(255))
  song_image = db.Column(db.String(120))
  time = db.Column(db.DateTime)

#record of all ratings that are submitted by users
class Ratings(db.Model):
  id = db.Column(db.Integer, primary_key=True, autoincrement=True)
  song_id = db.Column(db.Integer, db.ForeignKey('song.id'))
  username = db.Column(db.String, db.ForeignKey('user.username'))
  rating = db.Column(db.Integer)

#record of songs played by users
class SongLog(db.Model):
  id = db.Column(db.Integer, primary_key=True, autoincrement=True)
  song_id = db.Column(db.Integer, db.ForeignKey('song.id'))
  username = db.Column(db.String(80), db.ForeignKey('user.username'))
  time = db.Column(db.DateTime)


class Admin(db.Model):
  username = db.Column(db.String(80), primary_key=True)
  password = db.Column(db.String(80))


with app.app_context():
  #  db.drop_all()
  db.create_all()
  #  admin=Admin(username="ABC", password="pass")
  #  db.session.add(admin)
  #  db.session.commit()




# General utility functions

#function to add rating to songs
def add_rating_songs(songs):
  for song in songs:
    ratings = Ratings.query.filter_by(song_id=song.id).all()
    sum_r = sum(rating.rating for rating in ratings)
    song.rating = round((sum_r / len(ratings)), 2) if ratings else 0

  songs.sort(key=lambda x: x.rating, reverse=True)
  return songs

#function to add rating to albums
def add_rating_album(album):
  for alb in album:
    songs = Song.query.filter_by(album_id=alb.id).all()
    total = 0
    leng = 0
    for song in songs:
      ratings = Ratings.query.filter_by(song_id=song.id).all()
      song.rating = sum(rating.rating
                        for rating in ratings) / len(ratings) if ratings else 0
      if song.rating > 0:
        total += song.rating
        leng += 1
    alb.rating = round(total / leng, 2) if leng else 0
  album.sort(key=lambda x: x.rating, reverse=True)
  return album

#function to add rating to artists
def add_rating_artist(artists):
  for art in artists:
    songs = Song.query.filter_by(artist_name=art.username).all()
    total = 0
    leng = 0
    for song in songs:
      ratings = Ratings.query.filter_by(song_id=song.id).all()
      song.rating = sum(rating.rating
                        for rating in ratings) / len(ratings) if ratings else 0
      if song.rating > 0:
        total += song.rating
        leng += 1
    art.rating = round(total / leng, 2) if leng else 0
  artists.sort(key=lambda x: x.rating, reverse=True)
  return artists


#Controllers 

#Controllers- Users
@app.route('/')
def index():
  session['username'] = None
  session['admin'] = False
  return render_template("index.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
  if request.method == 'POST':
    username = request.form['username']
    password = request.form['password']
    user = User.query.filter_by(username=username).first()
    if user and (user.password == password):
      session['username'] = username
      return redirect(url_for('home'))
    else:
      flash('Login unsuccessful. Please check your username and password.',
            'danger')
      return render_template('login.html')
  else:
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
  if request.method == 'POST':
    username = request.form['username']
    password = request.form['password']
    email = request.form['email']
    conf_password = request.form['conf_password']
    user = User.query.filter_by(username=username).first()
    em = User.query.filter_by(email=email).first()

    if user:
      flash('User name already exists !', 'danger')
      return render_template('register.html')
    if em:
      flash('Email already exists !', 'danger')
      return render_template('register.html')
    if '@' not in email:
      flash('Enter a valid email id !', 'danger')
      return render_template('register.html')
    if conf_password != password:
      flash('Passwords do not match !', 'danger')
      return render_template('register.html')
    else:
      new_user = User(username=username,
                      password=password,
                      email=email,
                      creator=False,
                      profile_picture="../static/artist.png",
                      time=datetime.now())
      db.session.add(new_user)
      db.session.commit()
      return redirect(url_for('login'))
  else:
    return render_template('register.html')


@app.route('/home', methods=['GET', 'POST'])
def home():
  if request.method == 'POST':
    search_results = request.form["search"]
    return redirect(
        url_for('search_results',
                search_term=search_results,
                current_username=session.get('username')))
  else:
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    creator = user.creator
    songlog = SongLog.query.filter_by(username=username).order_by(
        desc(SongLog.time)).limit(6).all() #last played songs
    songs = []
    for log in songlog:
      x = Song.query.filter_by(id=log.song_id).first()
      if x in songs or not x:
        continue
      songs.append(x)
    songlog = (SongLog.query.filter_by(username=username).group_by(
        SongLog.song_id).order_by(desc(func.count(
            SongLog.song_id))).limit(6).all()) #most played songs
    song_favs = []
    for log in songlog:
      x = Song.query.filter_by(id=log.song_id).first()
      if not x:
        continue
      song_favs.append(x)
    highest_rated = Song.query.all()
    highest_rated = add_rating_songs(highest_rated)[:6] if len(
        highest_rated) > 6 else add_rating_songs(highest_rated) #highest rated songs
    recents = Album.query.order_by(desc(Album.time)).limit(6).all() #recently added albums
    return render_template('home.html',
                           username=username,
                           creator=creator,
                           songlog=songs,
                           song_favs=song_favs,
                           highest_rated=highest_rated,
                           recents=recents)


@app.route('/search_results/<string:search_term>', methods=['GET', 'POST'])
def search_results(search_term):
  if request.method == 'POST':
    search_results = request.form["search"]
    return redirect(
        url_for('search_results',
                search_term=search_results,
                current_username=session.get('username')))
  else:
    songs = Song.query.filter(Song.name.like(f"%{search_term}%")).all()
    songs = add_rating_songs(songs)
    album = Album.query.filter(Album.name.like(f"%{search_term}%")).all()
    album = add_rating_album(album)
    playlist = Playlist.query.filter(
        Playlist.name.like(f"%{search_term}%")).all()
    artist = Artist.query.filter(
        Artist.username.like(f"%{search_term}%")).all()
    artist = add_rating_artist(artist)
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    creator = user.creator
    return render_template('search_results.html',
                           search_term=search_term,
                           songs=songs,
                           album=album,
                           playlist=playlist,
                           artist=artist,
                           username=username,
                           current_username=session.get('username'),
                           creator=creator)


@app.route('/profile/<username>', methods=['GET', 'POST'])
def profile(username):
  logged_in_user = session.get("username")
  user = User.query.filter_by(username=username).first()
  print(user.creator)
  if request.method == 'POST':
    if "search" in request.form:
      search_results = request.form["search"]
      return redirect(
          url_for('search_results',
                  search_term=search_results,
                  current_username=session.get('username')))
    else:
      profile_pic = request.files["profile_pic"]
      path = os.path.join('static/profile', f'{username}.png')
      user.profile_picture = '../' + path
      db.session.commit()
      if user.creator:
        user.artist.profile_picture = '../' + path
        db.session.commit()
      profile_pic.save(path)
      return redirect(url_for('profile', username=username))
  else:
    if user.creator:
      songs = Song.query.filter_by(artist_name=user.username).all()
      songs = add_rating_songs(songs)
      albums = Album.query.filter_by(artist_name=user.username).all()
      albums = add_rating_album(albums)
      playlists = Playlist.query.filter_by(username=user.username).all()
      user = add_rating_artist([user])[0]
      return render_template('profile.html',
                             user=user,
                             current_user=logged_in_user,
                             songs=songs,
                             albums=albums,
                             playlists=playlists)
    else:
      playlists = Playlist.query.filter_by(username=user.username).all()

      return render_template('profile.html',
                             user=user,
                             current_user=logged_in_user,
                             playlists=playlists)

#register as creator
@app.route('/creator', methods=['GET', 'POST'])
def reg_creator():
  username = session.get('username')
  user = User.query.filter_by(username=username).first()
  if request.method == 'POST':
    action = request.form.get('action')
    if action == 'register':
      user.creator = True
      new_art = Artist(username=username,
                       profile_picture=user.profile_picture,
                       time=datetime.now())
      db.session.add(new_art)
      db.session.commit()
      return redirect(url_for("home"))

    elif action == 'redirect':
      return redirect(url_for("home"))
  else:
    if user.creator:
      return redirect(url_for('home'))
    return render_template('creator.html', username=session.get('username'))

#view album
@app.route("/album/<album>", methods=['GET', 'POST'])
def view_album(album):
  if request.method == 'POST':
    search_results = request.form["search"]
    return redirect(
        url_for('search_results',
                search_term=search_results,
                current_username=session.get('username')))
  else:
    logged_in_user = session.get('username')
    album = Album.query.filter_by(id=album).first()
    songs = Song.query.filter_by(album_id=album.id).all()
    songs = add_rating_songs(songs)
    album = add_rating_album([album])[0]
    user = User.query.filter_by(username=logged_in_user).first()
    creator = user.creator
    return (render_template('view_album.html',
                            logged_in_user=logged_in_user,
                            album=album,
                            songs=songs,creator=creator))


@app.route("/playlist/<playlist>", methods=['GET', 'POST'])
def view_playlist(playlist):
  if request.method == 'POST':
    search_results = request.form["search"]
    return redirect(
        url_for('search_results',
                search_term=search_results,
                current_username=session.get('username')))
  logged_in_user = session.get('username')
  ply = Playlist.query.filter_by(id=playlist).first()
  songs = ply.songs
  songs = add_rating_songs(songs)
  user = User.query.filter_by(username=logged_in_user).first()
  creator = user.creator
  return (render_template('view_playlist.html',
                          logged_in_user=logged_in_user,
                          playlist=ply,
                          songs=songs,creator=creator))


# Controllers-Artists


@app.route("/<username>/create/song", methods=['GET', 'POST'])
def create_song(username):
  logged_in_user = session.get("username")
  if logged_in_user != username:
    return redirect(url_for("home"))
  user = User.query.filter_by(username=username).first()
  if not user.creator:
    return redirect(url_for("reg_creator"))
  if request.method == 'POST':
    song_name = request.form.get('song_title')
    song_album = request.form.get('album_title')
    print(song_album)
    song_mp3 = request.files["mp3File"]
    song_pic = Album.query.get(song_album).album_picture if Album.query.get(
        song_album
    ).album_picture != '../static/album_icon.png' else "../static/music_icon.png"

    new_song = Song(name=song_name,
                    artist_name=username,
                    album_id=song_album,
                    path="",
                    song_image=song_pic,
                    time=datetime.now())
    db.session.add(new_song)
    db.session.commit()
    song_id = new_song.id
    directory_path = os.path.join('static/audio', username)
    if not os.path.exists(directory_path):
      os.makedirs(directory_path)
    path = os.path.join(directory_path, f'{song_id}.mp3')
    new_song.path = '../' + path
    db.session.commit()
    song_mp3.save(path)
    return redirect(url_for("home"))
  else:
    alb = Album.query.filter_by(artist_name=username).all()
    def_alb = alb.pop(-1) if alb else None
    return (render_template('create_song.html',
                            username=username,
                            albums=alb,
                            def_alb=def_alb))


@app.route("/<username>/create/album", methods=['GET', 'POST'])
def create_album(username):
  logged_in_user = session.get("username")
  if logged_in_user != username:
    return redirect(url_for("home"))
  user = User.query.filter_by(username=username).first()
  if not user.creator:
    return redirect(url_for("reg_creator"))
  if request.method == 'POST':
    album_name = request.form.get('album_name')
    album_picture = request.files["album_picture"]
    new_alb = Album(name=album_name,
                    artist_name=username,
                    album_picture="../static/album_icon.png",
                    time=datetime.now())
    db.session.add(new_alb)
    db.session.commit()
    if album_picture:
      directory_path = os.path.join('static/albums', username)
      if not os.path.exists(directory_path):
        os.makedirs(directory_path)
      path = os.path.join(directory_path, f'{new_alb.id}.png')
      new_alb.album_picture = '../' + path
      db.session.commit()
      album_picture.save(path)
    return redirect(url_for("create_song", username=username))
  else:
    return (render_template('create_album.html', username=username))


@app.route("/<username>/create/playlist", methods=['GET', 'POST'])
def create_playlist(username):
  logged_in_user = session.get("username")
  if logged_in_user != username:
    return redirect(url_for("home"))

  if request.method == 'POST':
    ply_name = request.form.get('playlist_name')
    playlist_picture = request.files["playlist_picture"]
    songs = []
    for key in request.form:
      if key.startswith('song'):
        song_id = request.form.get(key)
        songs.append(int(song_id))
    print(songs)
    new_ply = Playlist(name=ply_name,
                       username=username,
                       playlist_picture="../static/playlist_icon.png")
    db.session.add(new_ply)
    db.session.commit()
    songs = Song.query.filter(Song.id.in_(songs)).all()
    new_ply.songs.extend(songs)
    db.session.commit()
    if playlist_picture:
      directory_path = os.path.join('static/playlists', username)
      if not os.path.exists(directory_path):
        os.makedirs(directory_path)
      path = os.path.join(directory_path, f'{new_ply.id}.png')
      new_ply.playlist_picture = '../' + path
      db.session.commit()
      playlist_picture.save(path)
    return redirect(url_for("home"))
  else:
    songs = Song.query.all()
    return (render_template('create_playlist.html',
                            username=username,
                            songs=songs))


@app.route("/<username>/edit/playlist/<playlist>", methods=['GET', 'POST'])
def edit_playlist(username, playlist):
  logged_in_user = session.get("username")
  playlist = Playlist.query.filter_by(id=playlist).first()
  if logged_in_user != username:
    return redirect(url_for("home"))

  if request.method == 'POST':
    if 'edit' in request.form:
      playlist_picture = request.files["playlist_picture"]
      songs = []
      for key in request.form:
        if key.startswith('song'):
          song_id = request.form.get(key)
          songs.append(int(song_id))
      songs = Song.query.filter(Song.id.in_(songs)).all()
      playlist.songs.clear()
      playlist.songs.extend(songs)
      db.session.commit()
      if playlist_picture:
        directory_path = os.path.join('static/playlists', username)
        if not os.path.exists(directory_path):
          os.makedirs(directory_path)
        path = os.path.join(directory_path, f'{playlist.id}.png')
        playlist.playlist_picture = '../' + path
        db.session.commit()
        playlist_picture.save(path)
      return redirect(url_for("view_playlist", playlist=playlist.id))
    elif 'delete' in request.form:
      db.session.delete(playlist)
      db.session.commit()
      return redirect(url_for("home"))
  else:
    songs = Song.query.all()
    return (render_template('edit_playlist.html',
                            username=username,
                            songs=songs,
                            playlist=playlist))


@app.route("/<username>/edit/album/<album>", methods=['GET', 'POST'])
def edit_album(username, album):
  logged_in_user = session.get("username")
  curr_album = Album.query.filter_by(id=album).first()
  if logged_in_user != username:
    return redirect(url_for("home"))

  if request.method == 'POST':
    if 'edit' in request.form:
      album_picture = request.files["album_picture"]
      if album_picture:
        directory_path = os.path.join('static/albums', username)
        if not os.path.exists(directory_path):
          os.makedirs(directory_path)
        path = os.path.join(directory_path, f'{curr_album.id}.png')
        curr_album.album_picture = '../' + path
        db.session.commit()
        album_picture.save(path)
        songs = []
        for key in request.form:
          if key.startswith('song'):
            song_id = request.form.get(key)
            songs.append(int(song_id))
        songs = Song.query.filter(Song.id.in_(songs)).all()
        for song in songs:
          song.album_id = album
        album_songs = Song.query.filter_by(album_id=curr_album.id).all()
        for song in album_songs:
          song.song_image = curr_album.album_picture
          db.session.commit()
      return redirect(url_for("view_album", album=curr_album.id))
    elif 'delete' in request.form:
      db.session.delete(curr_album)
      db.session.commit()
      return redirect(url_for("home"))
  else:
    songs = Song.query.filter_by(artist_name=curr_album.artist_name).all()
    album_songs = Song.query.filter_by(album_id=curr_album.id).all()
    print(songs)
    return (render_template('edit_album.html',
                            username=username,
                            songs=songs,
                            album=curr_album,
                            album_songs=album_songs))


#Controllers-Backend

# To add rating, username and songid to ratings table
@app.route("/rating/<songId>/<username>/<rating>", methods=['GET', 'POST'])
def song_rating(songId, username, rating):
  ex_rating = Ratings.query.filter_by(song_id=songId,
                                      username=username).first()
  if ex_rating:
    ex_rating.rating = rating
    db.session.commit()
    print(ex_rating.rating, ex_rating.song_id, ex_rating.username)
  else:
    new_rating = Ratings(song_id=songId, username=username, rating=rating)
    db.session.add(new_rating)
    db.session.commit()
    print(new_rating.rating, new_rating.song_id, new_rating.username)
  return "sucess"

# to record songlog
@app.route('/song_clicked/<song_id>/<username>', methods=['GET', 'POST'])
def song_clicked(song_id, username):

  log = SongLog(song_id=song_id, username=username, time=datetime.now())
  db.session.add(log)
  db.session.commit()
  print(log.time, log.song_id, log.username)
  return ({'message': 'Song Click Logged!'})

# retreive information for admin dashboard
@app.route('/time/<category>', methods=['GET', 'POST'])
def retrieve_time(category):
  table_dict = {"User": User, "Artist": Artist, "Album": Album, "Song": Song}
  category = table_dict[category]
  twelve_hours_ago = datetime.now() - timedelta(hours=12)
  one_day_ago = datetime.now() - timedelta(days=1)
  one_week_ago = datetime.now() - timedelta(weeks=1)
  three_weeks_ago = datetime.now() - timedelta(weeks=3)
  within_12hrs = len(
      category.query.filter(category.time >= twelve_hours_ago).all())
  within_1day = len(
      category.query.filter(category.time <= twelve_hours_ago,
                            category.time >= one_day_ago).all())
  within_1week = len(
      category.query.filter(category.time <= one_day_ago,
                            category.time >= one_week_ago).all())
  within_3weeks = len(
      category.query.filter(category.time <= one_week_ago,
                            category.time >= three_weeks_ago).all())
  more_than3weeks = len(
      category.query.filter(category.time <= three_weeks_ago).all())
  data = [
      within_12hrs, within_1day, within_1week, within_3weeks, more_than3weeks
  ]
  data = {'data': data}
  print(data)
  status_code = 200

  response = make_response(jsonify(data), status_code)
  return response

# to delete artist, song,album or user
@app.route('/delete/<category>/<id>', methods=['DELETE'])
def delete_entry(category, id):
  if category == "Artist":
    entry = Artist.query.filter_by(username=id).first()
    user = User.query.filter_by(username=id).first()
    user.creator = False
    db.session.commit()

  elif category == "Album":
    entry = Album.query.filter_by(id=id).first()

  elif category == "Song":
    entry = Song.query.filter_by(id=id).first()

  elif category == "User":
    entry = User.query.filter_by(username=id).first()
  print(entry)
  db.session.delete(entry)
  db.session.commit()
  return ({'message': 'Deleted'})


# Controllers-Admin


@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
  if request.method == 'POST':
    username = request.form['username']
    password = request.form['password']
    admin = Admin.query.filter_by(username=username).first()
    if admin and (password == admin.password):
      session['admin'] = True
      return redirect(url_for('admin_dashboard'))
    else:
      flash('Login unsuccessful. Please check your username and password.',
            'danger')
      return render_template('admin_login.html')
  else:
    return render_template('admin_login.html')


@app.route('/admin', methods=['GET'])
def admin_dashboard():
  if session['admin']:
    users = User.query.all()
    artists = Artist.query.all()
    artists = add_rating_artist(artists)
    songs = Song.query.all()
    songs = add_rating_songs(songs)
    albums = Album.query.all()
    albums = add_rating_album(albums)
    songlog = SongLog.query.all()
    playlists = Playlist.query.all()
    return render_template('admin_dashboard.html',
                           playlists=playlists,
                           users=users,
                           artists=artists,
                           songs=songs,
                           albums=albums,
                           songlog=songlog)


@app.route('/detail/artist', methods=['GET'])
def detail_artist():
  if session['admin']:
    artists = Artist.query.all()
    artists = add_rating_artist(artists)
    return render_template("detailed_view_artist.html", artists=artists)


@app.route('/detail/album', methods=['GET'])
def detail_album():
  if session['admin']:
    albums = Album.query.all()
    albums = add_rating_album(albums)
    return render_template("detailed_view_album.html", albums=albums)


@app.route('/detail/user', methods=['GET'])
def detail_user():
  if session['admin']:
    users = User.query.all()
    return render_template("detailed_view_user.html", users=users)


@app.route('/detail/song', methods=['GET'])
def detail_song():
  if session['admin']:
    songs = Song.query.all()
    songs = add_rating_songs(songs)
    # for song in songs:
    #   album=Album.query.filter_by(id=song.album_id).first()
    #   song.album = album.name
    return render_template("detailed_view_song.html", songs=songs)


if __name__ == '__main__':
  app.run(host='0.0.0.0', port=81)
