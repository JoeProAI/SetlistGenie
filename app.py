import os
import json
from flask import Flask, request, render_template, jsonify, redirect, url_for, session
import firebase_admin
from firebase_admin import credentials, auth
import requests
from functools import wraps

# Initialize Flask app
app = Flask(__name__, template_folder='app/templates', static_folder='app/static')
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_secret_key")

# Initialize Firebase Admin SDK (server-side)
try:
    cred = credentials.Certificate(json.loads(os.environ.get("FIREBASE_ADMIN_CREDENTIALS", "{}")))
    firebase_admin.initialize_app(cred)
except (ValueError, firebase_admin.exceptions.FirebaseError):
    # In development, use a service account file if environment variable is not set
    try:
        cred = credentials.Certificate("firebase-service-account.json")
        firebase_admin.initialize_app(cred)
    except:
        print("Firebase Admin SDK initialization failed. Continuing without Firebase Admin.")

# Supabase client setup
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://cqlldqgxghuvbtmlaiec.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# Firebase Auth decorator
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        id_token = session.get('id_token')
        if not id_token:
            return redirect(url_for('login'))
        
        try:
            # Verify the ID token
            decoded_token = auth.verify_id_token(id_token)
            session['user_id'] = decoded_token['uid']
            return f(*args, **kwargs)
        except Exception as e:
            print(f"Authentication error: {e}")
            return redirect(url_for('login'))
    return decorated

# Route to serve the index/login page
@app.route('/')
def index():
    return render_template('index.html')

# Route to serve the login page
@app.route('/login')
def login():
    return render_template('login.html')

# Route to handle user session check
@app.route('/api/session/check', methods=['POST'])
def session_check():
    try:
        id_token = request.json.get('idToken')
        if not id_token:
            return jsonify({'authenticated': False}), 401
        
        # Verify the token with Firebase
        decoded_token = auth.verify_id_token(id_token)
        
        # Store user info in session
        session['id_token'] = id_token
        session['user_id'] = decoded_token['uid']
        
        return jsonify({
            'authenticated': True,
            'user': {
                'uid': decoded_token['uid'],
                'email': decoded_token.get('email', '')
            }
        })
    except Exception as e:
        print(f"Session check error: {e}")
        return jsonify({'authenticated': False, 'error': str(e)}), 401

# Route to handle logout
@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

# Dashboard route (protected)
@app.route('/dashboard')
@require_auth
def dashboard():
    return render_template('dashboard.html')

# API endpoint to get user's songs
@app.route('/api/songs', methods=['GET'])
@require_auth
def get_songs():
    user_id = session.get('user_id')
    
    # Fetch user's profile from Supabase
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}'
    }
    
    profile_response = requests.get(
        f"{SUPABASE_URL}/rest/v1/profiles?firebase_uid=eq.{user_id}&select=id",
        headers=headers
    )
    
    if profile_response.status_code != 200 or not profile_response.json():
        # Create profile if it doesn't exist
        profile_data = {'firebase_uid': user_id}
        profile_response = requests.post(
            f"{SUPABASE_URL}/rest/v1/profiles",
            headers=headers,
            json=profile_data
        )
        if profile_response.status_code != 201:
            return jsonify({'error': 'Failed to create user profile'}), 500
        
        # Fetch the newly created profile
        profile_response = requests.get(
            f"{SUPABASE_URL}/rest/v1/profiles?firebase_uid=eq.{user_id}&select=id",
            headers=headers
        )
    
    profile = profile_response.json()[0]
    profile_id = profile['id']
    
    # Fetch songs for this user
    songs_response = requests.get(
        f"{SUPABASE_URL}/rest/v1/songs?user_id=eq.{profile_id}&select=id,title,artist,duration,must_play,exclude_from_set",
        headers=headers
    )
    
    if songs_response.status_code != 200:
        return jsonify({'error': 'Failed to fetch songs'}), 500
    
    return jsonify(songs_response.json())

# API endpoint to add a new song
@app.route('/api/songs', methods=['POST'])
@require_auth
def add_song():
    user_id = session.get('user_id')
    song_data = request.json
    
    # Validate song data
    required_fields = ['title', 'artist', 'duration']
    for field in required_fields:
        if field not in song_data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    # Get user profile ID
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}'
    }
    
    profile_response = requests.get(
        f"{SUPABASE_URL}/rest/v1/profiles?firebase_uid=eq.{user_id}&select=id",
        headers=headers
    )
    
    if profile_response.status_code != 200 or not profile_response.json():
        return jsonify({'error': 'User profile not found'}), 404
    
    profile_id = profile_response.json()[0]['id']
    
    # Add the song
    song = {
        'user_id': profile_id,
        'title': song_data['title'],
        'artist': song_data['artist'],
        'duration': song_data['duration'],
        'must_play': song_data.get('must_play', False),
        'exclude_from_set': song_data.get('exclude_from_set', False)
    }
    
    response = requests.post(
        f"{SUPABASE_URL}/rest/v1/songs",
        headers=headers,
        json=song
    )
    
    if response.status_code != 201:
        return jsonify({'error': 'Failed to add song'}), 500
    
    return jsonify({'success': True, 'id': response.json().get('id')})

# API endpoint to delete a song
@app.route('/api/songs/<song_id>', methods=['DELETE'])
@require_auth
def delete_song(song_id):
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}'
    }
    
    response = requests.delete(
        f"{SUPABASE_URL}/rest/v1/songs?id=eq.{song_id}",
        headers=headers
    )
    
    if response.status_code != 204:
        return jsonify({'error': 'Failed to delete song'}), 500
    
    return jsonify({'success': True})

# API endpoint to generate a setlist
@app.route('/api/generate-setlist', methods=['POST'])
@require_auth
def api_generate_setlist():
    data = request.json
    user_id = session.get('user_id')
    
    # Validate input data
    required_fields = ['num_sets', 'set_duration']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    # Get user profile ID
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}'
    }
    
    profile_response = requests.get(
        f"{SUPABASE_URL}/rest/v1/profiles?firebase_uid=eq.{user_id}&select=id",
        headers=headers
    )
    
    if profile_response.status_code != 200 or not profile_response.json():
        return jsonify({'error': 'User profile not found'}), 404
    
    profile_id = profile_response.json()[0]['id']
    
    # Fetch songs for this user
    songs_response = requests.get(
        f"{SUPABASE_URL}/rest/v1/songs?user_id=eq.{profile_id}&select=id,title,artist,duration,must_play,exclude_from_set",
        headers=headers
    )
    
    if songs_response.status_code != 200:
        return jsonify({'error': 'Failed to fetch songs'}), 500
    
    songs = songs_response.json()
    
    # Filter out excluded songs
    songs = [song for song in songs if not song.get('exclude_from_set', False)]
    
    if not songs:
        return jsonify({'error': 'No songs available for setlist generation'}), 400
    
    # Import the setlist generator function
    from setlist_generator import generate_setlist
    
    # Generate the setlist
    result = generate_setlist(
        songs=songs,
        num_sets=data['num_sets'],
        set_duration=data['set_duration'],
        min_songs_between_artist=data.get('min_songs_between_artist', 3)
    )
    
    # Save the setlist if requested
    if data.get('save_setlist'):
        setlist_name = data.get('setlist_name', 'Untitled Setlist')
        
        # Create the setlist
        setlist_data = {
            'user_id': profile_id,
            'name': setlist_name,
            'description': data.get('description', '')
        }
        
        setlist_response = requests.post(
            f"{SUPABASE_URL}/rest/v1/setlists",
            headers=headers,
            json=setlist_data
        )
        
        if setlist_response.status_code != 201:
            return jsonify({'error': 'Failed to save setlist'}), 500
        
        setlist_id = setlist_response.json().get('id')
        
        # Add songs to the setlist
        for set_idx, set_data in enumerate(result['setlist']):
            for position, song in enumerate(set_data['songs']):
                setlist_song_data = {
                    'setlist_id': setlist_id,
                    'song_id': song['id'],
                    'position': position,
                    'set_number': set_idx + 1
                }
                
                requests.post(
                    f"{SUPABASE_URL}/rest/v1/setlist_songs",
                    headers=headers,
                    json=setlist_song_data
                )
    
    return jsonify(result)

# API endpoint to get saved setlists
@app.route('/api/setlists', methods=['GET'])
@require_auth
def get_setlists():
    user_id = session.get('user_id')
    
    # Get user profile ID
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}'
    }
    
    profile_response = requests.get(
        f"{SUPABASE_URL}/rest/v1/profiles?firebase_uid=eq.{user_id}&select=id",
        headers=headers
    )
    
    if profile_response.status_code != 200 or not profile_response.json():
        return jsonify([])
    
    profile_id = profile_response.json()[0]['id']
    
    # Fetch setlists for this user
    setlists_response = requests.get(
        f"{SUPABASE_URL}/rest/v1/setlists?user_id=eq.{profile_id}&select=id,name,description,created_at",
        headers=headers
    )
    
    if setlists_response.status_code != 200:
        return jsonify({'error': 'Failed to fetch setlists'}), 500
    
    return jsonify(setlists_response.json())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=False)
