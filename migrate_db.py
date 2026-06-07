"""
Run this ONCE to upgrade your existing interns.db:
  python migrate_db.py

It adds password_hash / password_plain columns to the intern table,
creates the hr_credentials table, and prints the generated passwords
for every existing intern so HR can share them.
"""
import sqlite3, hashlib, secrets

DB_PATH = 'interns.db'

def hp(pw): return hashlib.sha256(pw.encode()).hexdigest()
def gen_pw(): return secrets.token_urlsafe(6)

conn = sqlite3.connect(DB_PATH)

# 1. HR credentials table
conn.execute('''CREATE TABLE IF NOT EXISTS hr_credentials(
    id INTEGER PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT)''')
if not conn.execute('SELECT id FROM hr_credentials WHERE username=?',('hr',)).fetchone():
    conn.execute('INSERT INTO hr_credentials(username,password_hash) VALUES(?,?)',
                 ('hr', hp('hr123')))
    print('HR account created  → username: hr | password: hr123')
else:
    print('HR account already exists.')

# 2. Add columns if missing
cols = [r[1] for r in conn.execute('PRAGMA table_info(intern)').fetchall()]
if 'password_hash' not in cols:
    conn.execute('ALTER TABLE intern ADD COLUMN password_hash TEXT')
if 'password_plain' not in cols:
    conn.execute('ALTER TABLE intern ADD COLUMN password_plain TEXT')
if 'domain' not in cols:
    conn.execute('ALTER TABLE intern ADD COLUMN domain TEXT')
    print('✔ Added domain column to intern table')

# 3. Assign passwords to existing interns that don't have one
rows = conn.execute('SELECT id, name FROM intern WHERE password_hash IS NULL').fetchall()
print(f'\nGenerating passwords for {len(rows)} existing intern(s):\n')
print(f"{'ID':<5} {'Name':<25} {'Password'}")
print('-' * 45)
for row in rows:
    plain = gen_pw()
    conn.execute('UPDATE intern SET password_hash=?, password_plain=? WHERE id=?',
                 (hp(plain), plain, row[0]))
    print(f"{row[0]:<5} {row[1]:<25} {plain}")

conn.commit()
conn.close()
print('\n✅ Migration complete. Save the passwords above and share with each intern.')
