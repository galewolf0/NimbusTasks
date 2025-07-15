"""
Handles loading and saving tasks to disk, and provides utility functions for date formatting.
"""
import os
import sqlite3
from PyQt5.QtCore import QDate

DATA_DIR = 'data'
TASKS_DB = os.path.join(DATA_DIR, 'tasks.db')
COMPLETED_TASKS_DB = os.path.join(DATA_DIR, 'completed_tasks.db')

def ensure_db_files():
    """Ensure that the tasks.db and completed_tasks.db files exist in the data directory."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    if not os.path.exists(TASKS_DB):
        conn = sqlite3.connect(TASKS_DB)
        conn.close()
    if not os.path.exists(COMPLETED_TASKS_DB):
        conn = sqlite3.connect(COMPLETED_TASKS_DB)
        conn.close()

def date_to_str(qdate):
    """Convert QDate to string in yyyy-MM-dd format."""
    return qdate.toString('yyyy-MM-dd')

def add_task_to_db(date_str, text):
    """Insert a new incomplete task into tasks.db for the given date and text."""
    conn = sqlite3.connect(TASKS_DB)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            text TEXT NOT NULL
        )
    ''')
    c.execute('INSERT INTO tasks (date, text) VALUES (?, ?)', (date_str, text))
    conn.commit()
    conn.close()

def add_recurring_tasks_to_db(task_entries):
    """Insert multiple tasks at once using a single transaction for better performance."""
    conn = sqlite3.connect(TASKS_DB)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            text TEXT NOT NULL
        )
    ''')
    c.executemany('INSERT INTO tasks (date, text) VALUES (?, ?)', task_entries)
    conn.commit()
    conn.close()

def get_tasks_for_date(date_str):
    """Return a list of dicts with 'id' and 'text' for all tasks in tasks.db for the given date."""
    conn = sqlite3.connect(TASKS_DB)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            text TEXT NOT NULL
        )
    ''')
    c.execute('SELECT id, text FROM tasks WHERE date = ?', (date_str,))
    rows = c.fetchall()
    conn.close()
    return [{'id': row[0], 'text': row[1]} for row in rows]

def complete_task(task_id, date_str, text):
    """Copy the task to completed_tasks.db and remove it from tasks.db."""
    # Insert into completed_tasks.db
    conn_completed = sqlite3.connect(COMPLETED_TASKS_DB)
    c_completed = conn_completed.cursor()
    c_completed.execute('''
        CREATE TABLE IF NOT EXISTS completed_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            text TEXT NOT NULL
        )
    ''')
    c_completed.execute('INSERT INTO completed_tasks (date, text) VALUES (?, ?)', (date_str, text))
    conn_completed.commit()
    conn_completed.close()
    # Remove from tasks.db
    conn_tasks = sqlite3.connect(TASKS_DB)
    c_tasks = conn_tasks.cursor()
    c_tasks.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    conn_tasks.commit()
    conn_tasks.close()

def get_completed_tasks_for_date(date_str):
    """Return a list of dicts with 'id' and 'text' for all completed tasks for the given date."""
    conn = sqlite3.connect(COMPLETED_TASKS_DB)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS completed_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            text TEXT NOT NULL
        )
    ''')
    c.execute('SELECT id, text FROM completed_tasks WHERE date = ?', (date_str,))
    rows = c.fetchall()
    conn.close()
    return [{'id': row[0], 'text': row[1]} for row in rows]

def uncomplete_task(task_id, date_str, text):
    """Copy the task to tasks.db and remove it from completed_tasks.db, avoiding duplicates."""
    # Insert into tasks.db only if not already present
    conn_tasks = sqlite3.connect(TASKS_DB)
    c_tasks = conn_tasks.cursor()
    c_tasks.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            text TEXT NOT NULL
        )
    ''')
    c_tasks.execute('SELECT id FROM tasks WHERE date = ? AND text = ?', (date_str, text))
    exists = c_tasks.fetchone()
    if not exists:
        c_tasks.execute('INSERT INTO tasks (date, text) VALUES (?, ?)', (date_str, text))
        conn_tasks.commit()
    conn_tasks.close()
    # Remove from completed_tasks.db
    conn_completed = sqlite3.connect(COMPLETED_TASKS_DB)
    c_completed = conn_completed.cursor()
    c_completed.execute('DELETE FROM completed_tasks WHERE id = ?', (task_id,))
    conn_completed.commit()
    conn_completed.close()

def delete_task(task_id):
    """Delete a task from tasks.db by id."""
    conn = sqlite3.connect(TASKS_DB)
    c = conn.cursor()
    c.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()

def delete_completed_task(task_id):
    """Delete a task from completed_tasks.db by id."""
    conn = sqlite3.connect(COMPLETED_TASKS_DB)
    c = conn.cursor()
    c.execute('DELETE FROM completed_tasks WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()

def get_all_task_dates():
    """Return a set of all dates (as strings) that have any tasks (incomplete or completed)."""
    conn_tasks = sqlite3.connect(TASKS_DB)
    c_tasks = conn_tasks.cursor()
    c_tasks.execute('SELECT DISTINCT date FROM tasks')
    task_dates = {row[0] for row in c_tasks.fetchall()}
    conn_tasks.close()

    conn_completed = sqlite3.connect(COMPLETED_TASKS_DB)
    c_completed = conn_completed.cursor()
    c_completed.execute('SELECT DISTINCT date FROM completed_tasks')
    completed_dates = {row[0] for row in c_completed.fetchall()}
    conn_completed.close()

    return task_dates.union(completed_dates) 