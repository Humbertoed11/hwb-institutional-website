from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
import os

app = Flask(__name__)
DB_PATH = 'database/crm.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def dashboard():
    conn = get_db_connection()
    lead_count = conn.execute('SELECT COUNT(*) FROM Leads').fetchone()[0]
    opp_count = conn.execute('SELECT COUNT(*) FROM Opportunities').fetchone()[0]
    task_count = conn.execute('SELECT COUNT(*) FROM Tasks WHERE status != "Completed"').fetchone()[0]
    
    recent_leads = conn.execute('SELECT * FROM Leads ORDER BY created_at DESC LIMIT 5').fetchall()
    conn.close()
    return render_template('dashboard.html', 
                           lead_count=lead_count, 
                           opp_count=opp_count, 
                           task_count=task_count,
                           recent_leads=recent_leads)

# LEADS
@app.route('/leads')
def leads_list():
    conn = get_db_connection()
    leads = conn.execute('SELECT * FROM Leads ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('leads.html', leads=leads)

@app.route('/leads/add', methods=['GET', 'POST'])
def add_lead():
    if request.method == 'POST':
        company_name = request.form['company_name']
        source = request.form['source']
        status = request.form['status']
        assigned_to = request.form['assigned_to']
        
        conn = get_db_connection()
        conn.execute('INSERT INTO Leads (company_name, source, status, assigned_to) VALUES (?, ?, ?, ?)',
                     (company_name, source, status, assigned_to))
        conn.commit()
        conn.close()
        return redirect(url_for('leads_list'))
    return render_template('add_lead.html')

@app.route('/leads/edit/<int:id>', methods=['GET', 'POST'])
def edit_lead(id):
    conn = get_db_connection()
    lead = conn.execute('SELECT * FROM Leads WHERE lead_id = ?', (id,)).fetchone()
    
    if request.method == 'POST':
        company_name = request.form['company_name']
        source = request.form['source']
        status = request.form['status']
        assigned_to = request.form['assigned_to']
        
        conn.execute('UPDATE Leads SET company_name = ?, source = ?, status = ?, assigned_to = ?, updated_at = CURRENT_TIMESTAMP WHERE lead_id = ?',
                     (company_name, source, status, assigned_to, id))
        conn.commit()
        conn.close()
        return redirect(url_for('leads_list'))
    
    conn.close()
    return render_template('edit_lead.html', lead=lead)

@app.route('/childcare-leads')
def childcare_leads():
    conn = get_db_connection()
    leads = conn.execute('SELECT * FROM ChildcareData').fetchall()
    conn.close()
    return render_template('childcare_leads.html', leads=leads)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
