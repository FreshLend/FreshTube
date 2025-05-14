from flask import Flask, request, redirect, url_for, render_template, send_from_directory, session, request, jsonify
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import geoip2.database
import shutil, requests, os, re, json, random, string
from datetime import datetime
from PIL import Image

geoip2_db_path = 'static/ui/GeoLite2-Country.mmdb'

VIDEO_DATA_FILE = 'video_data.json'
USER_DATA_FILE = 'user_data.json'
COMMENTS_DATA_FILE = 'comments.json'
LIKES_DISLIKES_FILE = 'likes_dislakes.json'
COMMENT_LIKES_DISLIKES_FILE = 'comment_likes_dislakes.json'
CHANNEL_DATA_FILE = 'channels.json'

def load_data(file):
    if os.path.exists(file):
        try:
            with open(file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {file}: {e}")
        except Exception as e:
            print(f"Error reading {file}: {e}")
    return []

def save_data(file, data):
    try:
        with open(file, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving to {file}: {e}")

videos = load_data(VIDEO_DATA_FILE)
users = load_data(USER_DATA_FILE)
comments = load_data(COMMENTS_DATA_FILE)
likes_dislikes = load_data(LIKES_DISLIKES_FILE)
comment_likes_dislikes_data = load_data(COMMENT_LIKES_DISLIKES_FILE)
channels = load_data(CHANNEL_DATA_FILE)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/users'
app.config['UPLOAD_FOLDER_IMG'] = 'static/imgs'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

blocked_ips = ['']
blocked_countries = ['']
blocked_accs = ['']

app.config['SESSION_TYPE'] = 'filesystem'
app.config['SECRET_KEY'] = '32768:8:1$ZCprqFWU8MweZXkZ$f119a37b478e0374c6602cbf23fb5d45f82d92ce50f8482e566c1728a379fac28bde089db3c88c5af0138c6d4d6cb58bf4dcab1e5a6f13dccb501ef9c47839de'
app.config['SESSION_COOKIE_DOMAIN'] = '127.0.0.1'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True
Session(app)

def format_comment_text(text):
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    text = text.replace('\n', '<br>')
    url_pattern = re.compile(r'(https?://[^\s]+)')
    text = url_pattern.sub(r'<a href="\1">\1</a>', text)
    return text

app.jinja_env.filters['format_comment_text'] = format_comment_text

def time_ago(upload_date):
    now = datetime.now()
    diff = now - upload_date

    seconds = diff.total_seconds()
    
    if seconds < 60:
        count = int(seconds)
        return f"{count} {'секунда' if count == 1 else 'секунды' if count % 10 in [2, 3, 4] else 'секунд'} назад"
    elif seconds < 3600:
        count = int(seconds // 60)
        return f"{count} {'минута' if count == 1 else 'минуты' if count % 10 in [2, 3, 4] else 'минут'} назад"
    elif seconds < 86400:
        count = int(seconds // 3600)
        return f"{count} {'час' if count == 1 else 'часа' if count % 10 in [2, 3, 4] else 'часов'} назад"
    elif seconds < 2592000:
        count = int(seconds // 86400)
        return f"{count} {'день' if count == 1 else 'дня' if count % 10 in [2, 3, 4] else 'дней'} назад"
    elif seconds < 31536000:
        count = int(seconds // 2592000)
        return f"{count} {'месяц' if count == 1 else 'месяца' if count % 10 in [2, 3, 4] else 'месяцев'} назад"
    else:
        count = int(seconds // 31536000)
        return f"{count} {'год' if count == 1 else 'года' if count % 10 in [2, 3, 4] else 'лет'} назад"
    
def format_subscriber_count(count):
    if count >= 1_000_000_000:
        return f"{count // 1_000_000_000} млрд."
    elif count >= 1_000_000:
        return f"{count // 1_000_000} млн."
    elif count >= 1_000:
        return f"{count // 1_000} тыс."
    else:
        return str(count)

def get_country_by_ip(ip):
    try:
        with geoip2.database.Reader(geoip2_db_path) as reader:
            response = reader.country(ip)
            return response.country.iso_code
    except geoip2.errors.AddressNotFoundError:
        return None
    except Exception as e:
        return None

@app.before_request
def check_ip():
    client_ip = request.remote_addr
    if request.path.startswith('/static'):
        return None
    if client_ip in blocked_ips:
        return render_template('ip_not_allowed.html')
    country_code = get_country_by_ip(client_ip)
    if country_code and country_code in blocked_countries:
        return render_template('ip_not_allowed.html')
    return None

@app.before_request
def check_ban_acc():
    user_id = session.get('user_id')
    if request.path.startswith('/static'):
        return None
    if request.path.startswith('/logout'):
        return None
    if user_id and str(user_id) in blocked_accs:
        user = next((u for u in users if u['id'] == user_id), None)
        return render_template('you_are_banned.html', user_id=user_id, user=user)
        
    
@app.template_filter('format_number')
def format_number(number):
    if number >= 1_000_000_000:
        return f"{number / 1_000_000_000:.1f} млрд."
    elif number >= 1_000_000:
        return f"{number / 1_000_000:.1f} млн."
    elif number >= 1_000:
        return f"{number / 1_000:.1f} тыс."
    else:
        return str(number)

@app.route('/robots.txt')
def robots():
    return render_template('robots.txt')
    
@app.route('/sitemap.xml')
def sitemap():
    return render_template('sitemap.xml')

@app.route('/ip_not_allowed.html')
def ip_not_allowed():
    return render_template('ip_not_allowed.html')

@app.route('/you_are_banned.html')
def you_are_banned():
    return render_template('you_are_banned.html')

@app.route('/')
def index():
    sorted_videos = sorted(videos, key=lambda v: v['likes'] - v['dislikes'], reverse=True)
    for video in sorted_videos:
        video['relative_time'] = time_ago(datetime.fromisoformat(video['upload_date']))
    user_id = session.get('user_id')
    user = next((u for u in users if u['id'] == user_id), None)
    user_theme = session.get('theme', 'black')
    return render_template('index.html', videos=sorted_videos, user=user, user_id=user_id, user_theme=user_theme)

@app.route('/search')
def search():
    query = request.args.get('q', '').strip().lower()
    
    if query:
        filtered_videos = [
            video for video in videos if query in video['title'].lower() or query in video['description'].lower()
        ]
    else:
        filtered_videos = []
    user_id = session.get('user_id')
    user = next((u for u in users if u['id'] == user_id), None)
    return render_template('search.html', query=query, videos=filtered_videos, user=user, user_id=user_id)

@app.route('/search_videos')
def search_videos():
    query = request.args.get('query', '').strip().lower()
    offset = int(request.args.get('offset', 0))
    limit = 24

    if query:
        filtered_videos = [
            video for video in videos if query in video['title'].lower() or query in video['description'].lower()
        ]
    else:
        filtered_videos = []

    next_videos = filtered_videos[offset:offset + limit]
    all_videos_loaded = len(next_videos) < limit
    base_static_url = url_for('static', filename='')

    return jsonify({'videos': next_videos, 'static_url': base_static_url, 'all_videos_loaded': all_videos_loaded})

@app.route('/load_more_videos')
def load_more_videos():
    offset = int(request.args.get('offset', 0))
    limit = 24
    sorted_videos = sorted(videos, key=lambda v: v['likes'] - v['dislikes'], reverse=True)
    for video in sorted_videos:
        video['relative_time'] = time_ago(datetime.fromisoformat(video['upload_date']))
    next_videos = sorted_videos[offset:offset + limit]
    all_videos_loaded = len(next_videos) < limit
    base_static_url = url_for('static', filename='')
    return jsonify({'videos': next_videos, 'static_url': base_static_url, 'all_videos_loaded': all_videos_loaded})

@app.route('/watch')
def video():
    video_id = request.args.get('si', type=str)
    video = next((v for v in videos if v['id'] == video_id), None)
    if video is None:
        return "Видео не найдено.", 404
    video['relative_time'] = time_ago(datetime.fromisoformat(video['upload_date']))
    video_comments = [
        {
            **c,
            'user': next((u for u in users if u['id'] == c['user_id']), None)
        }
        for c in comments if c['video_id'] == video_id and 'user_id' in c
    ]
    video_comments.sort(key=lambda c: c['likes'], reverse=True)
    for comment in video_comments:
        comment['sub_comments'] = [
            {
                **sub_comment,
                'user': next((u for u in users if u['id'] == sub_comment['user_id']), None)
            }
            for sub_comment in comment.get('sub_comments', [])
        ]
    channel = next((ch for ch in channels if ch['id'] == video['channel_id']), None)
    user_id = session.get('user_id')
    user = next((u for u in users if u['id'] == user_id), None)
    video_user = next((u for u in users if u['id'] == video['user_id']), None)
    subscribers = len(channel.get('subscribers', []))
    formatted_subscribers = format_subscriber_count(subscribers)
    return render_template('watch.html', formatted_subscribers=formatted_subscribers, video=video, comments=video_comments, channel=channel, video_user=video_user, user=user)

@app.route('/channel')
def channel():
    channel_id = request.args.get('id', type=str)
    if channel_id is None:
        return "Канал не найден", 404
    channel = next((ch for ch in channels if ch['id'] == channel_id), None)
    if channel is None:
        return "Канал не найден", 404
    user_id = channel['user_id']
    user = next((u for u in users if u['id'] == user_id), None)
    if user:
        channel['avatar'] = user.get('avatar', 'user.png')
        channel['name'] = user.get('nickname', 'Неизвестный')
    else:
        channel['avatar'] = 'user.png'
        channel['name'] = 'Неизвестный'
    user_videos = [v for v in videos if v.get('channel_id') == channel['id']]
    user_videos.sort(key=lambda v: datetime.fromisoformat(v['upload_date']), reverse=True)
    for video in user_videos:
        video['relative_time'] = time_ago(datetime.fromisoformat(video['upload_date']))
    subscribers = len(channel.get('subscribers', []))
    formatted_subscribers = format_subscriber_count(subscribers)
    user_id_from_session = session.get('user_id')
    return render_template('channel.html', formatted_subscribers=formatted_subscribers, user=user, channel=channel, videos=user_videos, user_id=user_id_from_session)

@app.route('/settings')
def settings():
    user_id = session.get('user_id')
    user = next((u for u in users if u['id'] == user_id), None)
    return render_template('settings.html', user=user, user_id=user_id)

@app.route('/publish')
def publish():
	return render_template('publish.html')
	
@app.route('/signin')
def signin():
	return render_template('login.html')
	
@app.route('/signup')
def signup():
	return render_template('register.html')

def generate_video_id(length=11):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

@app.route('/upload', methods=['POST'])
def upload():
    if 'video' not in request.files or 'cover' not in request.files:
        return redirect(request.url)
    video_file = request.files['video']
    cover_file = request.files['cover']
    title = request.form.get('title', '')
    description = request.form.get('description', '')
    if 'user_id' not in session:
        return redirect(url_for('register'))
    user_id = session['user_id']
    user = next((u for u in users if u['id'] == user_id), None)
    if not user:
        return "Пользователь не найден.", 404
    formatted_description = format_comment_text(description)
    channels = load_data(CHANNEL_DATA_FILE)
    channel = next((c for c in channels if c['user_id'] == user_id), None)
    if not channel:
        return redirect(url_for('404'))
    channel_id = channel['id']
    if video_file and cover_file:
        video_id = generate_video_id()
        video_filename = f"{video_id}.mp4"
        cover_filename = f"{video_id}.webp"
        user_folder = os.path.join(app.config['UPLOAD_FOLDER'], f'user_{user_id}')
        if not os.path.exists(user_folder):
            os.makedirs(user_folder)
        video_folder = os.path.join(user_folder, 'videos')
        img_folder = os.path.join(user_folder, 'imgs')
        if not os.path.exists(video_folder):
            os.makedirs(video_folder)
        if not os.path.exists(img_folder):
            os.makedirs(img_folder)
        try:
            video_path = os.path.join(video_folder, video_filename)
            video_file.save(video_path)
            cover_path = os.path.join(img_folder, cover_filename)
            with Image.open(cover_file) as img:
                img = img.resize((640, 360))
                img = img.convert("RGB")
                img.save(cover_path, format='WebP')
            upload_date = datetime.now().isoformat()
            new_video = {
                'id': video_id,
                'user_id': user_id,
                'filename': f"user_{user_id}/videos/{video_filename}",
                'cover': f"user_{user_id}/imgs/{cover_filename}",
                'title': title,
                'description': formatted_description,
                "channel_id": channel_id,
                'likes': 0,
                'dislikes': 0,
                'views': 0,
                'upload_date': upload_date
            }
            videos.append(new_video)
            save_data(VIDEO_DATA_FILE, videos)
        except Exception as e:
            return f"Ошибка при загрузке: {str(e)}", 500
    return redirect(url_for('index'))

@app.route('/like_dislike', methods=['POST'])
def like_dislike():
    video_id = str(request.form['video_id'])
    action = request.form['action']
    user_id = session.get('user_id')
    if not user_id or not any(user['id'] == user_id for user in users):
        return redirect(url_for('register'))
    video = next((v for v in videos if v['id'] == video_id), None)
    if video is None:
        return "Video not found", 404
    video_likes_dislikes = next((vd for vd in likes_dislikes if vd['video_id'] == video_id), None)
    if video_likes_dislikes is None:
        video_likes_dislikes = {'video_id': video_id, 'likes': [], 'dislikes': []}
        likes_dislikes.append(video_likes_dislikes)
    if action == 'like':
        if user_id in video_likes_dislikes['dislikes']:
            video_likes_dislikes['dislikes'].remove(user_id)
            video['dislikes'] -= 1
        if user_id in video_likes_dislikes['likes']:
            video_likes_dislikes['likes'].remove(user_id)
            video['likes'] -= 1
        else:
            video_likes_dislikes['likes'].append(user_id)
            video['likes'] += 1
    elif action == 'dislike':
        if user_id in video_likes_dislikes['likes']:
            video_likes_dislikes['likes'].remove(user_id)
            video['likes'] -= 1
        if user_id in video_likes_dislikes['dislikes']:
            video_likes_dislikes['dislikes'].remove(user_id)
            video['dislikes'] -= 1
        else:
            video_likes_dislikes['dislikes'].append(user_id)
            video['dislikes'] += 1
    else:
        return "Invalid action", 400
    save_data(VIDEO_DATA_FILE, videos)
    save_data(LIKES_DISLIKES_FILE, likes_dislikes)
    return redirect(url_for('video', si=video_id))

@app.route('/vote', methods=['POST'])
def vote():
    comment_id = int(request.form['comment_id'])
    action = request.form['action']
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('register'))
    comment = next((c for c in comments if c['id'] == comment_id), None)
    if comment is None:
        return "Comment not found", 404
    comment_likes_dislikes = next((cld for cld in comment_likes_dislikes_data if cld['comment_id'] == comment_id), None)
    if comment_likes_dislikes is None:
        comment_likes_dislikes = {'comment_id': comment_id, 'likes': [], 'dislikes': []}
        comment_likes_dislikes_data.append(comment_likes_dislikes)
    if action == 'like':
        if user_id in comment_likes_dislikes['dislikes']:
            comment_likes_dislikes['dislikes'].remove(user_id)
            comment['dislikes'] = comment.get('dislikes', 0) - 1
        if user_id in comment_likes_dislikes['likes']:
            comment_likes_dislikes['likes'].remove(user_id)
            comment['likes'] = comment.get('likes', 0) - 1
        else:
            comment_likes_dislikes['likes'].append(user_id)
            comment['likes'] = comment.get('likes', 0) + 1
    elif action == 'dislike':
        if user_id in comment_likes_dislikes['likes']:
            comment_likes_dislikes['likes'].remove(user_id)
            comment['likes'] = comment.get('likes', 0) - 1
        if user_id in comment_likes_dislikes['dislikes']:
            comment_likes_dislikes['dislikes'].remove(user_id)
            comment['dislikes'] = comment.get('dislikes', 0) - 1
        else:
            comment_likes_dislikes['dislikes'].append(user_id)
            comment['dislikes'] = comment.get('dislikes', 0) + 1
    else:
        return "Invalid action", 400
    save_data(COMMENTS_DATA_FILE, comments)
    save_data(COMMENT_LIKES_DISLIKES_FILE, comment_likes_dislikes_data)
    return redirect(url_for('video', si=comment.get('video_id')))

@app.route('/subscribe', methods=['POST'])
def subscribe():
    user_id = session.get('user_id')
    channel_id = str(request.form['channel_id'])
    if not user_id or not any(user['id'] == user_id for user in users):
        return redirect(url_for('register'))
    channel = next((c for c in channels if c['id'] == channel_id), None)
    if channel is None:
        return "Channel not found", 404
    if user_id == channel['user_id']:
        return "You cannot subscribe to your own channel", 400
    if user_id not in channel['subscribers']:
        channel['subscribers'].append(user_id)
        save_data('channels.json', channels)
    return redirect(request.referrer or url_for('channel', id=channel_id))

@app.route('/unsubscribe', methods=['POST'])
def unsubscribe():
    user_id = session.get('user_id')
    channel_id = str(request.form['channel_id'])
    if not user_id or not any(user['id'] == user_id for user in users):
        return redirect(url_for('register'))
    channel = next((c for c in channels if c['id'] == channel_id), None)
    if channel is None:
        return "Channel not found", 404
    if user_id == channel['user_id']:
        return "You cannot unsubscribe from your own channel", 400
    if user_id in channel['subscribers']:
        channel['subscribers'].remove(user_id)
        save_data('channels.json', channels)
    else:
        return "You are not subscribed to this channel", 400
    return redirect(request.referrer or url_for('channel', id=channel_id))

@app.route('/add_comment', methods=['POST'])
def add_comment():
    global comments
    if 'user_id' not in session:
        return redirect(url_for('register'))
    user_id = session['user_id']
    video_id = request.form.get('video_id', type=str)
    comment_text = request.form.get('comment')
    if not video_id or not comment_text:
        return "Недостаточно данных для добавления комментария.", 400
    user = next((u for u in users if u['id'] == user_id), None)
    channel_id = next((ch for ch in channels if ch['user_id'] == user['id']), None)
    if user is None:
        return "Пользователь не найден.", 404
    def generate_comment_id():
        if comments:
            return max(comment['id'] for comment in comments) + 1
        return 1
    new_comment_id = generate_comment_id()
    new_comment = {
        'id': new_comment_id,
        'video_id': video_id,
        'user_id': user_id,
        'channel_link_id': channel_id,
        'text': format_comment_text(comment_text),
        'likes': 0,
        'dislikes': 0,
        'sub_comments': []
    }
    comments.append(new_comment)
    comments.sort(key=lambda c: c['likes'], reverse=True)
    save_data(COMMENTS_DATA_FILE, comments)
    return redirect(url_for('video', si=video_id))

@app.route('/add_sub_comment', methods=['POST'])
def add_sub_comment():
    if 'user_id' not in session:
        return redirect(url_for('register'))
    user_id = session['user_id']
    parent_id = int(request.form['parent_id'])
    text = request.form['text']
    user = next((u for u in users if u['id'] == user_id), None)
    channel_id = next((ch for ch in channels if ch['user_id'] == user['id']), None)
    if user is None:
        return "Пользователь не найден.", 404
    def generate_sub_comment_id(parent_comment):
        if parent_comment['sub_comments']:
            return max(sc['id'] for sc in parent_comment['sub_comments']) + 1
        return 1
    parent_comment = next((c for c in comments if c['id'] == parent_id), None)
    if parent_comment:
        new_sub_comment_id = generate_sub_comment_id(parent_comment)
        sub_comment = {
            'id': new_sub_comment_id,
            'user_id': user_id,
            'channel_link_id': channel_id,
            'text': text
        }
        parent_comment['sub_comments'].append(sub_comment)
        save_data(COMMENTS_DATA_FILE, comments)
    return redirect(url_for('video', si=parent_comment['video_id']))

@app.route('/static/<path:filename>')
def custom_static(filename):
    return send_from_directory('static', filename)

def generate_nickname():
    length = random.randint(1, 50)
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_channel_id():
    length = random.randint(3, 30)
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        avatar = request.files.get('avatar')
        nickname = generate_nickname()
        channel_id = generate_channel_id()
        while any(u['nickname'] == nickname for u in users):
            nickname = generate_nickname()
        while any(u['id'] == channel_id for u in channels):
            channel_id = generate_channel_id()
        if any(u['email'] == email for u in users):
            return "Пользователь с таким email уже существует.", 400
        user_id = len(users) + 1
        avatar_filename = f"avatar_{user_id}.jpg"
        if avatar:
            try:
                upload_folder = app.config['UPLOAD_FOLDER_IMG']
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)
                img = Image.open(avatar)
                img = img.resize((128, 128))
                img.save(os.path.join(upload_folder, avatar_filename))
            except Exception as e:
                return f"Ошибка при сохранении аватара: {e}", 500
        else:
            try:
                default_avatar_path = os.path.join('static', 'ui', 'user.png')
                destination_path = os.path.join(app.config['UPLOAD_FOLDER_IMG'], avatar_filename)
                shutil.copy(default_avatar_path, destination_path)
            except Exception as e:
                return f"Ошибка при сохранении аватара по умолчанию: {e}", 500
        new_user = {
            'id': user_id,
            'nickname': nickname,
            'email': email,
            'password': generate_password_hash(password),
            'avatar': avatar_filename,
            'group': "user",
            'theme': "black"
        }
        users.append(new_user)
        save_data(USER_DATA_FILE, users)
        new_channel = {
            'id': channel_id,
            'user_id': new_user['id'],
            'description': "Без описания",
            'subscribers': []
        }
        channels.append(new_channel)
        save_data(CHANNEL_DATA_FILE, channels)
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = next((u for u in users if u['email'] == email), None)
        channel = next((ch for ch in channels if ch['user_id'] == user['id']), None)
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['channel_id'] = channel['id']
            session['avatar'] = user.get('avatar')
            session['theme'] = user.get('theme', 'black')
            return redirect(url_for('index'))
        return "Неверный email или пароль.", 400
    return render_template('login.html')

@app.route('/logout')
def logout():
    user_id = session.get('user_id')
    if user_id:
        session.pop('avatar', None)
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/save-avatar', methods=['POST'])
def save_avatar():
    if 'user_id' not in session:
        return redirect(url_for('register'))
    user_id = session['user_id']
    if 'avatar' not in request.files:
        return "No file part", 400
    file = request.files['avatar']
    if file.filename == '':
        return "No selected file", 400
    filename = secure_filename(f"avatar_{user_id}.jpg")
    upload_folder = app.config['UPLOAD_FOLDER_IMG']
    try:
        img = Image.open(file)
        img = img.resize((128, 128))
        img.save(os.path.join(upload_folder, filename))
    except Exception as e:
        return f"Error saving avatar: {e}", 500
    user = next((u for u in users if u['id'] == user_id), None)
    if user:
        user['avatar'] = filename
        save_data('user_data.json', users)
    else:
        return "User not found", 404
    user_channel = next((ch for ch in channels if ch['user_id'] == user_id), None)
    if user_channel:
        channel_id = user_channel['id']
        return redirect(url_for('channel', id=channel_id))
    else:
        return "Channel not found", 404

@app.route('/save-nickname', methods=['POST'])
def save_nickname():
    if 'user_id' not in session:
        return redirect(url_for('register'))
    user_id = session['user_id']
    new_nickname = request.form.get('nickname')
    if len(new_nickname) > 50:
        return "Никнейм не может быть длиннее 50 символов", 400
    user = next((u for u in users if u['id'] == user_id), None)
    if user:
        user['nickname'] = new_nickname
        save_data('user_data.json', users)
        user_channel = next((ch for ch in channels if ch['user_id'] == user_id), None)
        if user_channel:
            channel_id = user_channel['id']
            return redirect(url_for('channel', id=channel_id))
        else:
            return "Channel not found", 404
    else:
        return "User not found", 404

@app.route('/save-description', methods=['POST'])
def save_description():
    if 'user_id' not in session:
        return redirect(url_for('register'))
    user_id = session['user_id']
    description = request.form.get('description')
    if not description:
        return "Описание не может быть пустым", 400
    user_channel = next((ch for ch in channels if ch['user_id'] == user_id), None)
    if not user_channel:
        return "Канал не найден", 404
    user_channel['description'] = description
    save_data(CHANNEL_DATA_FILE, channels)
    return redirect(url_for('channel', id=user_channel['id']))

@app.route('/update_theme', methods=['POST'])
def update_theme():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('register'))
    new_theme = request.form.get('theme')
    user = next((u for u in users if u['id'] == user_id), None)
    if user:
        user['theme'] = new_theme
        save_data(USER_DATA_FILE, users)
        session['theme'] = new_theme
        return redirect(url_for('settings'))
    return 'User not found', 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=43034, debug=True) # ssl_context=("fullchain.crt", "certificate.key"),