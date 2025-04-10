-- SetlistGenie Simplified Database Schema
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

-- For now, simplify by allowing all authenticated users to access
CREATE POLICY "Allow authenticated users for profiles"
  ON profiles FOR ALL TO authenticated USING (true)
  WITH CHECK (true);

CREATE POLICY "Allow authenticated users for songs"
  ON songs FOR ALL TO authenticated USING (true)
  WITH CHECK (true);

CREATE POLICY "Allow authenticated users for setlists"
  ON setlists FOR ALL TO authenticated USING (true)
  WITH CHECK (true);

CREATE POLICY "Allow authenticated users for setlist_songs"
  ON setlist_songs FOR ALL TO authenticated USING (true)
  WITH CHECK (true);
