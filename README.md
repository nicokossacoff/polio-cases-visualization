# Polio Dashboard - Render.com Deployment

This is a Dash web application that visualizes global polio vaccination coverage and case data from 1980-2016.

## Features

- **Interactive Charts**: Stacked area charts showing polio cases by income groups over time
- **Animated Maps**: Global choropleth maps with scatter overlays showing vaccination coverage vs. cases
- **Responsive Design**: Mobile-friendly interface with tabs for different visualizations

## Files for Deployment

### Required Files
- `app.py` - Main application file (deployment-ready version)
- `requirements.txt` - Python dependencies
- `render.yaml` - Render.com service configuration
- `data/` folder - Contains all CSV data files

### Data Files Required
- `country_metadata.csv`
- `global-vaccination-coverage.csv`
- `number-of-estimated-paralytic-polio-cases-by-world-region.csv`
- `total_population.csv`

## Deployment Steps on Render.com

### Method 1: Using render.yaml (Recommended)

1. **Push to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit - Polio Dashboard"
   git branch -M main
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

2. **Deploy on Render**:
   - Go to [render.com](https://render.com)
   - Sign up/Login with your GitHub account
   - Click "New" → "Blueprint"
   - Connect your GitHub repository
   - Render will automatically detect the `render.yaml` file
   - Click "Apply" to deploy

### Method 2: Manual Setup

1. **Create Web Service**:
   - Go to Render Dashboard
   - Click "New" → "Web Service"
   - Connect your GitHub repository

2. **Configure Service**:
   - **Name**: `polio-dash-app`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:server`
   - **Plan**: Free (or choose your preferred plan)

3. **Deploy**: Click "Create Web Service"

## Local Testing

Before deploying, test locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

Visit `http://localhost:8050` to test the dashboard.

## Environment Variables

The app uses these environment variables:
- `PORT` - Server port (automatically set by Render)

## Key Changes for Deployment

The deployment version (`app.py`) includes these modifications:
1. Added `server = app.server` for WSGI compatibility
2. Changed host to `0.0.0.0` and port to use environment variable
3. Disabled debug mode for production
4. Added `os` import for environment variables

## Troubleshooting

**Common Issues:**
1. **Build fails**: Check that all data files are included in the repository
2. **App crashes**: Verify CSV file paths are correct and files exist
3. **Memory issues**: Consider upgrading to a paid plan for larger datasets

**Resource Requirements:**
- Free tier should work for this app
- Data files total ~2MB
- App uses pandas for data processing which needs adequate memory

## Tech Stack

- **Frontend**: Dash, Plotly
- **Backend**: Python, Pandas
- **Deployment**: Gunicorn WSGI server
- **Platform**: Render.com
