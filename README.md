# SetlistGenie

A lightweight, cost-optimized application for musicians to manage songs and generate setlists.

## Features

- Firebase Authentication
- Song Management (Add, Delete, List)
- Smart Setlist Generation with constraints:
  - Set duration
  - Number of sets
  - Artist spacing
  - Must-play songs
- Saved Setlists
- Mobile-friendly design

## Deployment Guide

### Prerequisites

- Google Cloud account with billing enabled
- Firebase project (pauliecee-ba4e0)
- Supabase project

### Step 1: Set up Supabase Database

Run the following SQL in your Supabase SQL Editor:

```sql
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
  ON songs FOR SELECT USING (user_id IN (SELECT id FROM profiles WHERE firebase_uid = auth.uid()));

CREATE POLICY "Users can insert their own songs." 
  ON songs FOR INSERT WITH CHECK (user_id IN (SELECT id FROM profiles WHERE firebase_uid = auth.uid()));

CREATE POLICY "Users can update own songs." 
  ON songs FOR UPDATE USING (user_id IN (SELECT id FROM profiles WHERE firebase_uid = auth.uid()));

CREATE POLICY "Users can delete own songs." 
  ON songs FOR DELETE USING (user_id IN (SELECT id FROM profiles WHERE firebase_uid = auth.uid()));

-- Similar policies for setlists
CREATE POLICY "Setlists are viewable by users who created them." 
  ON setlists FOR SELECT USING (user_id IN (SELECT id FROM profiles WHERE firebase_uid = auth.uid()));

CREATE POLICY "Users can insert their own setlists." 
  ON setlists FOR INSERT WITH CHECK (user_id IN (SELECT id FROM profiles WHERE firebase_uid = auth.uid()));

CREATE POLICY "Users can update own setlists." 
  ON setlists FOR UPDATE USING (user_id IN (SELECT id FROM profiles WHERE firebase_uid = auth.uid()));

CREATE POLICY "Users can delete own setlists." 
  ON setlists FOR DELETE USING (user_id IN (SELECT id FROM profiles WHERE firebase_uid = auth.uid()));

-- Policies for setlist songs
CREATE POLICY "Setlist songs are viewable by users who created the parent setlist." 
  ON setlist_songs FOR SELECT USING (
    setlist_id IN (
      SELECT id FROM setlists WHERE user_id IN (
        SELECT id FROM profiles WHERE firebase_uid = auth.uid()
      )
    )
  );

CREATE POLICY "Users can insert setlist songs to their own setlists." 
  ON setlist_songs FOR INSERT WITH CHECK (
    setlist_id IN (
      SELECT id FROM setlists WHERE user_id IN (
        SELECT id FROM profiles WHERE firebase_uid = auth.uid()
      )
    )
  );

CREATE POLICY "Users can delete setlist songs from their own setlists." 
  ON setlist_songs FOR DELETE USING (
    setlist_id IN (
      SELECT id FROM setlists WHERE user_id IN (
        SELECT id FROM profiles WHERE firebase_uid = auth.uid()
      )
    )
  );
```

### Step 2: Firebase Service Account

1. Go to Firebase Console > Project Settings > Service Accounts
2. Click "Generate new private key"
3. Download the JSON file
4. Keep it secure - you'll need it for deployment

### Step 3: Cloud Run Deployment

1. **Build and push the container**

```bash
# Navigate to project directory
cd SetlistGenie

# Build the container
gcloud builds submit --tag gcr.io/pauliecee-ba4e0/setlistgenie

# Deploy to Cloud Run (minimal instance size for cost optimization)
gcloud run deploy setlistgenie \
  --image gcr.io/pauliecee-ba4e0/setlistgenie \
  --platform managed \
  --region us-east1 \
  --memory 256Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 2 \
  --set-env-vars FLASK_SECRET_KEY=YOUR_SECRET_KEY \
  --set-env-vars SUPABASE_URL=https://cqlldqgxghuvbtmlaiec.supabase.co \
  --set-env-vars SUPABASE_KEY=YOUR_SUPABASE_ANON_KEY
```

2. **Set Firebase credentials**

```bash
# Encode the Firebase service account JSON file to base64
cat firebase-service-account.json | base64

# Update the service with the encoded credentials
gcloud run services update setlistgenie \
  --update-env-vars FIREBASE_ADMIN_CREDENTIALS=PASTE_BASE64_ENCODED_JSON_HERE
```

### Step 4: Set Up DNS

1. Get the URL from your deployed Cloud Run service
2. Set up a custom domain mapping in Cloud Run for setlist.pauliecee.com
3. Configure your DNS provider with the provided verification records
4. Wait for DNS propagation

## Local Development

```bash
# Set environment variables
export FLASK_SECRET_KEY=your_secret_key
export SUPABASE_URL=https://cqlldqgxghuvbtmlaiec.supabase.co
export SUPABASE_KEY=your_supabase_anon_key
export FIREBASE_ADMIN_CREDENTIALS='{...}' # Your Firebase service account JSON

# Run the application
python app.py
```

## Cost Optimization Features

1. **Minimal Instance Size**: 256MB memory, 1 CPU
2. **Scale to Zero**: No costs when not in use 
3. **Efficient Database Schema**: Optimized for minimal reads/writes
4. **No External Libraries**: Minimal CSS/JS for faster loading
5. **Optimized Images**: No heavy assets
6. **Caching Headers**: Set for static resources

## Troubleshooting

- **Firebase Auth Issues**: Check Firebase console for auth errors
- **Database Errors**: Verify Supabase RLS policies
- **Deployment Failures**: Check Cloud Build logs

## Security Notes

- Never commit API keys or service account files to repositories
- Use environment variables for all sensitive information
- Firebase service account has elevated privileges - keep secure
