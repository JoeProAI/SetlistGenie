-- SetlistGenie Database Schema
-- For Supabase project: https://cqlldqgxghuvbtmlaiec.supabase.co

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create profiles table to link with Firebase Auth
CREATE TABLE IF NOT EXISTS profiles (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  firebase_uid TEXT UNIQUE NOT NULL,
  username TEXT,
  email TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create songs table
CREATE TABLE IF NOT EXISTS songs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  artist TEXT NOT NULL,
  duration INTEGER NOT NULL,
  must_play BOOLEAN DEFAULT FALSE,
  exclude_from_set BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create setlists table
CREATE TABLE IF NOT EXISTS setlists (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create setlist_songs table
CREATE TABLE IF NOT EXISTS setlist_songs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  setlist_id UUID REFERENCES setlists(id) ON DELETE CASCADE,
  song_id UUID REFERENCES songs(id) ON DELETE CASCADE,
  position INTEGER NOT NULL,
  set_number INTEGER NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE songs ENABLE ROW LEVEL SECURITY;
ALTER TABLE setlists ENABLE ROW LEVEL SECURITY;
ALTER TABLE setlist_songs ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY "Public profiles are viewable by users who created them." 
  ON profiles FOR SELECT USING (auth.uid() = firebase_uid);

CREATE POLICY "Users can insert their own profile." 
  ON profiles FOR INSERT WITH CHECK (auth.uid() = firebase_uid);

CREATE POLICY "Users can update own profile." 
  ON profiles FOR UPDATE USING (auth.uid() = firebase_uid);

-- Policies for songs, setlists, and setlist_songs
CREATE POLICY "Songs are viewable by users who created them." 
  ON songs FOR SELECT USING (user_id IN (SELECT id FROM profiles WHERE firebase_uid = auth.uid()::text));

CREATE POLICY "Users can insert their own songs." 
  ON songs FOR INSERT WITH CHECK (user_id IN (SELECT id FROM profiles WHERE firebase_uid = auth.uid()::text));

CREATE POLICY "Users can update own songs." 
  ON songs FOR UPDATE USING (user_id IN (SELECT id FROM profiles WHERE firebase_uid = auth.uid()::text));

CREATE POLICY "Users can delete own songs." 
  ON songs FOR DELETE USING (user_id IN (SELECT id FROM profiles WHERE firebase_uid = auth.uid()::text));

-- Similar policies for setlists
CREATE POLICY "Setlists are viewable by users who created them." 
  ON setlists FOR SELECT USING (user_id IN (SELECT id FROM profiles WHERE firebase_uid = auth.uid()::text));

CREATE POLICY "Users can insert their own setlists." 
  ON setlists FOR INSERT WITH CHECK (user_id IN (SELECT id FROM profiles WHERE firebase_uid = auth.uid()::text));

CREATE POLICY "Users can update own setlists." 
  ON setlists FOR UPDATE USING (user_id IN (SELECT id FROM profiles WHERE firebase_uid = auth.uid()::text));

CREATE POLICY "Users can delete own setlists." 
  ON setlists FOR DELETE USING (user_id IN (SELECT id FROM profiles WHERE firebase_uid = auth.uid()::text));

-- Policies for setlist songs
CREATE POLICY "Setlist songs are viewable by users who created the parent setlist." 
  ON setlist_songs FOR SELECT USING (
    setlist_id IN (
      SELECT id FROM setlists WHERE user_id IN (
        SELECT id FROM profiles WHERE firebase_uid = auth.uid()::text
      )
    )
  );

CREATE POLICY "Users can insert setlist songs to their own setlists." 
  ON setlist_songs FOR INSERT WITH CHECK (
    setlist_id IN (
      SELECT id FROM setlists WHERE user_id IN (
        SELECT id FROM profiles WHERE firebase_uid = auth.uid()::text
      )
    )
  );

CREATE POLICY "Users can delete setlist songs from their own setlists." 
  ON setlist_songs FOR DELETE USING (
    setlist_id IN (
      SELECT id FROM setlists WHERE user_id IN (
        SELECT id FROM profiles WHERE firebase_uid = auth.uid()::text
      )
    )
  );
