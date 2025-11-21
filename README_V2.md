# FGU Character Sheet Generator - Web Version (V2)

Convert Fantasy Grounds Unity XML character files to beautiful, responsive HTML character sheets.

## Features

- ✓ Web-based interface (no desktop installation needed)
- ✓ Fully responsive (works on mobile, tablet, desktop)
- ✓ Drag & drop file upload
- ✓ Beautiful D&D 5e themed design
- ✓ All character data extracted automatically
- ✓ Interactive spell slots and sorcery points
- ✓ Printable HTML output
- ✓ One-click download

## Deployment Options

### Option 1: Deploy on Vercel (Easiest)

1. **Sign up** at https://vercel.com (free account)

2. **Push to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git push origin main
   ```

3. **Deploy from Vercel Dashboard**:
   - Click "New Project"
   - Import your GitHub repository
   - Vercel auto-detects the Python app
   - Click "Deploy"

Your app is live!

### Option 2: Deploy on Heroku

1. **Install Heroku CLI**: https://devcenter.heroku.com/articles/heroku-cli

2. **Create Procfile**:
   ```
   web: gunicorn proyectocsFGU_V2:app
   ```

3. **Deploy**:
   ```bash
   heroku login
   heroku create your-app-name
   git push heroku main
   ```

### Option 3: Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python proyectocsFGU_V2.py

# Open browser to http://localhost:5000
```

## How to Use

1. **Export from Fantasy Grounds Unity**:
   - Right-click character → Export → XML
   - Save the XML file

2. **Upload to the web app**:
   - Go to the deployed site
   - Drag & drop or click to upload XML
   - Click "Generate Character Sheet"

3. **Download & Use**:
   - Save HTML file to your computer
   - Open in any web browser
   - Print to PDF or paper

## File Structure

```
├── proyectocsFGU_V2.py      # Main Flask application
├── requirements.txt          # Python dependencies
├── vercel.json              # Vercel configuration
└── README.md                # This file
```

## Technologies Used

- **Python 3.8+** with Flask web framework
- **XML parsing** for FGU character data
- **Responsive HTML/CSS** for all device sizes
- **JavaScript** for interactive features

## Browser Support

- Chrome/Chromium (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)
- Mobile browsers

## Troubleshooting

**Upload fails with "File must be XML format"**
- Ensure you exported the file as XML from FGU
- Check file extension is .xml

**Generated HTML looks broken**
- Clear browser cache and reload
- Try opening in a different browser
- Check file is valid FGU export

**Deployment issues on Vercel**
- Check requirements.txt has all dependencies
- Verify vercel.json configuration
- Check build logs in Vercel dashboard

## Performance

- Cold start: ~3 seconds (Vercel)
- Generation time: <1 second
- Max file size: 16 MB
- Concurrent users: Unlimited (auto-scaling)

## Security

- Files are processed in memory (not stored)
- XML validation before parsing
- Secure file upload (type checking)
- No external data collection

## License

This tool is provided as-is for personal use with Fantasy Grounds Unity.

## Support

For issues or questions, check the character sheet output for error messages or review the uploaded XML file format.
