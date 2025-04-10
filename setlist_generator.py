def generate_setlist(songs, num_sets, set_duration, min_songs_between_artist=4):
    """
    Generate a setlist with the given constraints
    
    Args:
        songs: List of song dictionaries with title, artist, duration, must_play, and exclude_from_set
        num_sets: Number of sets to generate
        set_duration: Duration of each set in seconds
        min_songs_between_artist: Minimum number of songs between songs by the same artist
    
    Returns:
        Dictionary containing the setlist and extras
    """
    import random
    
    setlist = []
    used_songs = set()
    
    def can_add_artist(artist, set_songs, min_spacing):
        """Check if an artist can be added based on spacing requirements"""
        recent_artists = [song['artist'] for song in set_songs[-min_spacing:]]
        return artist not in recent_artists
    
    # Sort songs by must_play first
    must_play_songs = [song for song in songs if song.get('must_play', False)]
    optional_songs = [song for song in songs if not song.get('must_play', False)]
    
    for set_num in range(num_sets):
        current_set = []
        current_duration = 0
        
        # Try to add must-play songs first
        for song in must_play_songs[:]:
            if (song['title'] not in used_songs and 
                current_duration + song['duration'] <= set_duration and
                (not current_set or can_add_artist(song['artist'], current_set, min_songs_between_artist))):
                current_set.append(song)
                current_duration += song['duration']
                used_songs.add(song['title'])
                must_play_songs.remove(song)
        
        # Fill remaining time with optional songs
        available_songs = [song for song in optional_songs 
                         if song['title'] not in used_songs]
        random.shuffle(available_songs)
        
        for song in available_songs:
            if (current_duration + song['duration'] <= set_duration and
                (not current_set or can_add_artist(song['artist'], current_set, min_songs_between_artist))):
                current_set.append(song)
                current_duration += song['duration']
                used_songs.add(song['title'])
        
        setlist.append({
            'songs': current_set,
            'duration': current_duration
        })
    
    # Collect unused songs as extras
    extras = ([song for song in must_play_songs] +
             [song for song in optional_songs if song['title'] not in used_songs])
    
    return {
        'setlist': setlist,
        'extras': extras
    }
