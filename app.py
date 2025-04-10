import os
import json
import csv
import io
import requests
import firebase_admin
from firebase_admin import credentials, auth
from flask import Flask, request, render_template, jsonify, redirect, url_for, session, send_file, Response
from functools import wraps
from datetime import datetime

# Get the absolute path to the templates folder
base_dir = os.path.abspath(os.path.dirname(__file__))
templates_dir = os.path.join(base_dir, 'app', 'templates')
static_dir = os.path.join(base_dir, 'app', 'static')

# Print paths for debugging
print(f"Base directory: {base_dir}")
print(f"Templates directory: {templates_dir}")
print(f"Static directory: {static_dir}")

# Check if templates directory exists
if os.path.exists(templates_dir):
    print(f"Templates directory exists: {os.listdir(templates_dir)}")
else:
    print(f"Templates directory does not exist!")

# Initialize Flask app
app = Flask(__name__, template_folder=templates_dir, static_folder=static_dir)
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

# CSV Import route - Upload a CSV file of songs
@app.route('/api/import-csv', methods=['POST'])
@require_auth
def import_csv():
    user_id = session.get('user_id')
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'File must be a CSV'}), 400
    
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
    
    try:
        # Read the CSV file
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.DictReader(stream)
        
        # Track imported songs
        imported = 0
        errors = []
        
        for row in csv_reader:
            try:
                # Extract data from CSV row
                song_data = {
                    'user_id': profile_id,
                    'title': row.get('title', '').strip(),
                    'artist': row.get('artist', '').strip(),
                    'duration': int(row.get('duration', 0)) if row.get('duration') else 0,
                    'energy': int(row.get('energy', 5)) if row.get('energy') else 5,
                    'key': row.get('key', '').strip(),
                    'bpm': int(row.get('bpm', 0)) if row.get('bpm') else 0,
                    'must_play': str(row.get('must_play', '')).lower() in ['true', 'yes', '1'],
                    'exclude_from_set': str(row.get('exclude_from_set', '')).lower() in ['true', 'yes', '1']
                }
                
                # Validate required fields
                if not song_data['title'] or not song_data['artist']:
                    errors.append(f"Row missing title or artist: {row}")
                    continue
                
                # Add song to database
                song_response = requests.post(
                    f"{SUPABASE_URL}/rest/v1/songs",
                    headers={
                        'apikey': SUPABASE_KEY,
                        'Authorization': f'Bearer {SUPABASE_KEY}',
                        'Content-Type': 'application/json',
                        'Prefer': 'return=representation'
                    },
                    json=song_data
                )
                
                if song_response.status_code == 201:
                    imported += 1
                else:
                    errors.append(f"Failed to import {song_data['title']}: {song_response.text}")
            
            except Exception as e:
                errors.append(f"Error processing row: {str(e)}")
        
        return jsonify({
            'success': True,
            'message': f"Successfully imported {imported} songs",
            'errors': errors
        })
        
    except Exception as e:
        return jsonify({'error': f"Error processing CSV: {str(e)}"}), 500

# CSV Template route - Download a template CSV file
@app.route('/api/csv-template')
@require_auth
def download_csv_template():
    # Create a CSV template with headers and example rows
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow(['title', 'artist', 'duration', 'energy', 'key', 'bpm', 'must_play', 'exclude_from_set'])
    
    # Write example rows
    writer.writerow(['My Song Title', 'Artist Name', '180', '7', 'C Major', '120', 'no', 'no'])
    writer.writerow(['Another Song', 'Different Artist', '240', '4', 'A Minor', '95', 'yes', 'no'])
    
    # Prepare the response
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=setlistgenie_template.csv"
        }
    )

# Export Setlist route - Download a setlist as CSV
@app.route('/api/export-setlist/<int:setlist_id>')
@require_auth
def export_setlist(setlist_id):
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
        return jsonify({'error': 'User profile not found'}), 404
    
    profile_id = profile_response.json()[0]['id']
    
    # Get setlist details
    setlist_response = requests.get(
        f"{SUPABASE_URL}/rest/v1/setlists?id=eq.{setlist_id}&user_id=eq.{profile_id}",
        headers=headers
    )
    
    if setlist_response.status_code != 200 or not setlist_response.json():
        return jsonify({'error': 'Setlist not found'}), 404
    
    setlist = setlist_response.json()[0]
    
    # Get setlist songs with joined song data
    songs_response = requests.get(
        f"{SUPABASE_URL}/rest/v1/setlist_songs?setlist_id=eq.{setlist_id}&select=position,set_number,songs(title,artist,duration,energy,key,bpm)",
        headers=headers
    )
    
    if songs_response.status_code != 200:
        return jsonify({'error': 'Failed to fetch setlist songs'}), 500
    
    setlist_songs = songs_response.json()
    
    # Create CSV file
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow(['Set', 'Position', 'Title', 'Artist', 'Duration (sec)', 'Energy', 'Key', 'BPM'])
    
    # Write song rows
    for item in setlist_songs:
        song = item.get('songs', {})
        writer.writerow([
            item.get('set_number', 1),
            item.get('position', 0) + 1,  # Make positions 1-based for human readability
            song.get('title', ''),
            song.get('artist', ''),
            song.get('duration', 0),
            song.get('energy', 0),
            song.get('key', ''),
            song.get('bpm', 0)
        ])
    
    # Prepare the response
    output.seek(0)
    safe_name = ''.join(c if c.isalnum() else '_' for c in setlist.get('name', 'setlist'))
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={safe_name}.csv"
        }
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=False)
