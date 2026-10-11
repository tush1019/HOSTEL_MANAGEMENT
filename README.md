# Hostel Management

A simple hostel management web app built with Flask for tracking rooms, student records, and payments.

## Features
- Dashboard with occupancy and revenue overview
- Room management for adding and viewing room inventory
- Student registration with room assignment and check-in dates
- Payment tracking and recent payment history
- SQLite-backed data storage

## Quick start

1. Create and activate a virtual environment if needed.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the application:
   ```bash
   python app.py
   ```
4. Open http://localhost:5000 in your browser.

## API smoke checks
- GET /health returns application status
- GET /api/summary returns summary JSON

## Testing
```bash
pytest -q
```