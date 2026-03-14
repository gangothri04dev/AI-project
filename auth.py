import sqlite3
import hashlib
import os
import json
import pandas as pd
import resend

DB_PATH = "users.db"
# Use a default from address for Resend unless specified
RESEND_FROM_EMAIL = "onboarding@resend.dev"

def init_db():
    """Initialize the users database"""
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''CREATE TABLE users
                    (id INTEGER PRIMARY KEY,
                     username TEXT UNIQUE NOT NULL,
                     password TEXT NOT NULL,
                     email TEXT UNIQUE NOT NULL,
                     recovery_code TEXT,
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        c.execute('''CREATE TABLE analysis_history
                    (id INTEGER PRIMARY KEY,
                     user_id INTEGER NOT NULL,
                     file_name TEXT NOT NULL,
                     file_size INTEGER,
                     num_rows INTEGER,
                     num_columns INTEGER,
                     date_column TEXT,
                     numeric_columns TEXT,
                     summary_stats TEXT,
                     file_data TEXT,
                     predictions TEXT,
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                     FOREIGN KEY(user_id) REFERENCES users(id))''')
        
        conn.commit()
        conn.close()
    else:
        # Check if analysis_history table exists, if not create it
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='analysis_history'")
        if not c.fetchone():
            c.execute('''CREATE TABLE analysis_history
                        (id INTEGER PRIMARY KEY,
                         user_id INTEGER NOT NULL,
                         file_name TEXT NOT NULL,
                         file_size INTEGER,
                         num_rows INTEGER,
                         num_columns INTEGER,
                         date_column TEXT,
                         numeric_columns TEXT,
                         summary_stats TEXT,
                         file_data TEXT,
                         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                         FOREIGN KEY(user_id) REFERENCES users(id))''')
            conn.commit()
        else:
            # Check if columns exist, if not add them
            c.execute("PRAGMA table_info(analysis_history)")
            columns = [column[1] for column in c.fetchall()]
            if 'file_data' not in columns:
                c.execute("ALTER TABLE analysis_history ADD COLUMN file_data TEXT")
                conn.commit()
            if 'predictions' not in columns:
                c.execute("ALTER TABLE analysis_history ADD COLUMN predictions TEXT")
                conn.commit()
        conn.close()

def hash_password(password):
    """Hash a password for security"""
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, email, password):
    """Register a new user
    Returns: (success: bool, message: str)
    """
    try:
        init_db()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Check if username already exists
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        if c.fetchone():
            return False, "Username already exists. Please choose a different one."
        
        # Check if email already exists
        c.execute("SELECT * FROM users WHERE email = ?", (email,))
        if c.fetchone():
            return False, "Email already registered. Please use a different email."
        
        # Validate password length
        if len(password) < 6:
            return False, "Password must be at least 6 characters long."
        
        # Insert new user
        hashed_pw = hash_password(password)
        c.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                 (username, email, hashed_pw))
        conn.commit()
        conn.close()
        
        return True, "Registration successful! You can now login."
    except Exception as e:
        return False, f"Registration error: {str(e)}"

def login_user(username, password):
    """Login a user
    Returns: (success: bool, message: str, user_data: dict or None)
    """
    try:
        init_db()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        hashed_pw = hash_password(password)
        c.execute("SELECT * FROM users WHERE username = ? AND password = ?",
                 (username, hashed_pw))
        user = c.fetchone()
        conn.close()
        
        if user:
            user_data = {
                'id': user[0],
                'username': user[1],
                'email': user[3]
            }
            return True, "Login successful!", user_data
        else:
            return False, "Invalid username or password.", None
    except Exception as e:
        return False, f"Login error: {str(e)}", None

def get_user_data(username):
    """Get user data by username"""
    try:
        init_db()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("SELECT id, username, email FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()
        
        if user:
            return {
                'id': user[0],
                'username': user[1],
                'email': user[2]
            }
        return None
    except Exception as e:
        print(f"Error getting user data: {str(e)}")
        return None

def send_recovery_email(email, code):
    """Send recovery code using Resend API"""
    api_key = os.environ.get("EMAIL_SERVICE_API_KEY")
    if not api_key:
        return False, "Email API key not configured. Please add EMAIL_SERVICE_API_KEY to secrets."
    
    try:
        resend.api_key = api_key
        params = {
            "from": RESEND_FROM_EMAIL,
            "to": email,
            "subject": "Your Password Recovery Code - An AI That Converts Chaos into Clarity",
            "html": f"""
            <h2>Password Recovery</h2>
            <p>You requested to reset your password.</p>
            <p><strong>Your recovery code is: {code}</strong></p>
            <p>This code will expire shortly. If you did not request this, please ignore this email.</p>
            """
        }
        resend.Emails.send(params)
        return True, "Recovery code sent to your email"
    except Exception as e:
        print(f"Email send error: {str(e)}")
        return False, f"Failed to send email: {str(e)}"

def reset_password_request(email):
    """Generate code and send recovery email"""
    try:
        init_db()
        import random
        import string
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("SELECT username FROM users WHERE email = ?", (email,))
        user = c.fetchone()
        
        if user:
            # Generate a 6-digit numeric code
            code = ''.join(random.choices(string.digits, k=6))
            c.execute("UPDATE users SET recovery_code = ? WHERE email = ?", (code, email))
            conn.commit()
            conn.close()
            
            # Send real email
            success, email_msg = send_recovery_email(email, code)
            if success:
                return True, f"Recovery code has been sent to {email}."
            else:
                return False, email_msg
        else:
            conn.close()
            return False, "No account found with that email address."
    except Exception as e:
        return False, f"Recovery error: {str(e)}"

def verify_code_and_reset_password(email, code, new_password):
    """Verify the code and reset the password"""
    try:
        init_db()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("SELECT recovery_code FROM users WHERE email = ?", (email,))
        result = c.fetchone()
        
        if result and result[0] == code:
            hashed_pw = hash_password(new_password)
            c.execute("UPDATE users SET password = ?, recovery_code = NULL WHERE email = ?", (hashed_pw, email))
            conn.commit()
            conn.close()
            return True, "Password reset successful! You can now login."
        else:
            conn.close()
            return False, "Invalid recovery code."
    except Exception as e:
        return False, f"Reset error: {str(e)}"

def save_analysis(user_id, file_name, file_size, num_rows, num_columns, date_column, numeric_columns, summary_stats, file_data=None, predictions=None):
    """Save analysis results to history"""
    try:
        init_db()
        import json
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        numeric_cols_json = json.dumps(numeric_columns)
        
        # Convert DataFrame to dict if needed
        if hasattr(summary_stats, 'to_dict'):
            summary_stats_json = json.dumps(summary_stats.to_dict())
        else:
            summary_stats_json = json.dumps(summary_stats if summary_stats else {})
        
        # Convert file_data (DataFrame) to JSON string
        file_data_json = None
        if file_data is not None and hasattr(file_data, 'to_json'):
            file_data_json = file_data.to_json()
        
        # Convert predictions to JSON string
        predictions_json = None
        if predictions is not None:
            if hasattr(predictions, 'to_json'):
                predictions_json = predictions.to_json()
            else:
                predictions_json = json.dumps(predictions)
        
        c.execute("""INSERT INTO analysis_history 
                    (user_id, file_name, file_size, num_rows, num_columns, date_column, numeric_columns, summary_stats, file_data, predictions)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                 (user_id, file_name, file_size, num_rows, num_columns, date_column, numeric_cols_json, summary_stats_json, file_data_json, predictions_json))
        conn.commit()
        conn.close()
        return True, "Analysis saved to history"
    except Exception as e:
        return False, f"Error saving analysis: {str(e)}"

def get_user_analysis_history(user_id, limit=10):
    """Get user's analysis history"""
    try:
        init_db()
        import json
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("""SELECT id, file_name, num_rows, num_columns, date_column, created_at 
                    FROM analysis_history 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT ?""", (user_id, limit))
        
        results = c.fetchall()
        conn.close()
        
        history = []
        for row in results:
            history.append({
                'id': row[0],
                'file_name': row[1],
                'num_rows': row[2],
                'num_columns': row[3],
                'date_column': row[4],
                'created_at': row[5]
            })
        return history
    except Exception as e:
        print(f"Error fetching history: {str(e)}")
        return []

def get_analysis_by_id(analysis_id):
    """Get a specific analysis by ID"""
    try:
        init_db()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("""SELECT file_data, file_name, date_column, numeric_columns, predictions 
                    FROM analysis_history 
                    WHERE id = ?""", (analysis_id,))
        
        result = c.fetchone()
        conn.close()
        
        if result:
            file_data_json = result[0]
            file_name = result[1]
            date_column = result[2]
            numeric_columns_json = result[3]
            predictions_json = result[4]
            
            if file_data_json:
                try:
                    file_data = pd.read_json(file_data_json)
                    numeric_columns = json.loads(numeric_columns_json) if numeric_columns_json else []
                    
                    predictions = None
                    if predictions_json:
                        try:
                            predictions = pd.read_json(predictions_json)
                        except:
                            predictions = json.loads(predictions_json)
                    
                    return True, file_data, file_name, date_column, numeric_columns, predictions
                except Exception as parse_err:
                    print(f"Error parsing JSON data: {str(parse_err)}")
                    return False, None, None, None, None, None
        
        return False, None, None, None, None, None
    except Exception as e:
        print(f"Error retrieving analysis: {str(e)}")
        return False, None, None, None, None, None
