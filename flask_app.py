from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from mysql.connector import Error
import os

app = Flask(__name__)
app.secret_key = 'chiave_segreta_per_flash_messages'  # Necessaria per i flash messages

# Configurazione del database
DB_CONFIG = {}

def load_db_config():
    """Carica la configurazione del database dal file connessione.txt"""
    global DB_CONFIG
    try:
        with open('connessione.txt', 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                # Ignora righe vuote e commenti
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        DB_CONFIG[key.strip()] = value.strip()
    except FileNotFoundError:
        print("ERRORE: File connessione.txt non trovato!")
        print("Crea il file con i parametri di connessione MySQL")
        exit(1)

def get_db_connection():
    """Crea una connessione al database MySQL"""
    try:
        connection = mysql.connector.connect(
            host=DB_CONFIG['HOST'],
            port=int(DB_CONFIG['PORT']),
            database=DB_CONFIG['DATABASE'],
            user=DB_CONFIG['USERNAME'],
            password=DB_CONFIG['PASSWORD']
        )
        return connection
    except Error as e:
        print(f"Errore durante la connessione al database: {e}")
        return None

def init_database():
    """Inizializza il database creando le tabelle se non esistono"""
    conn = get_db_connection()
    if conn is None:
        print("Impossibile connettersi al database!")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Tabella immobili
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS immobili (
                id INT AUTO_INCREMENT PRIMARY KEY,
                indirizzo VARCHAR(255) NOT NULL,
                citta VARCHAR(100) NOT NULL,
                prezzo DECIMAL(12,2) NOT NULL,
                metratura INT NOT NULL,
                descrizione TEXT,
                disponibile BOOLEAN NOT NULL DEFAULT TRUE,
                data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabella clienti
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clienti (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nome VARCHAR(100) NOT NULL,
                cognome VARCHAR(100) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                telefono VARCHAR(20) NOT NULL,
                data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        print("Database inizializzato con successo!")
        return True
        
    except Error as e:
        print(f"Errore durante l'inizializzazione del database: {e}")
        return False
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# Route principale - Dashboard
@app.route('/')
def index():
    """Pagina principale con statistiche generali"""
    conn = get_db_connection()
    if conn is None:
        flash('Errore di connessione al database!', 'error')
        return render_template('index.html', immobili_totali=0, immobili_disponibili=0, clienti_totali=0)
    
    try:
        cursor = conn.cursor()
        
        # Statistiche per la dashboard
        cursor.execute('SELECT COUNT(*) FROM immobili')
        immobili_totali = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM immobili WHERE disponibile = TRUE')
        immobili_disponibili = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM clienti')
        clienti_totali = cursor.fetchone()[0]
        
        return render_template('index.html', 
                             immobili_totali=immobili_totali,
                             immobili_disponibili=immobili_disponibili,
                             clienti_totali=clienti_totali)
        
    except Error as e:
        flash(f'Errore nel recupero delle statistiche: {e}', 'error')
        return render_template('index.html', immobili_totali=0, immobili_disponibili=0, clienti_totali=0)
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# GESTIONE IMMOBILI

@app.route('/immobili')
def immobili():
    """Visualizza la lista di tutti gli immobili"""
    conn = get_db_connection()
    if conn is None:
        flash('Errore di connessione al database!', 'error')
        return render_template('immobili.html', immobili=[])
    
    try:
        cursor = conn.cursor(dictionary=True)  # Restituisce risultati come dizionari
        cursor.execute('SELECT * FROM immobili ORDER BY id DESC')
        immobili = cursor.fetchall()
        return render_template('immobili.html', immobili=immobili)
        
    except Error as e:
        flash(f'Errore nel recupero degli immobili: {e}', 'error')
        return render_template('immobili.html', immobili=[])
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/aggiungi_immobile')
def aggiungi_immobile():
    """Mostra il form per aggiungere un nuovo immobile"""
    return render_template('modifica_immobile.html', immobile=None)

@app.route('/modifica_immobile/<int:id>')
def modifica_immobile(id):
    """Mostra il form per modificare un immobile esistente"""
    conn = get_db_connection()
    if conn is None:
        flash('Errore di connessione al database!', 'error')
        return redirect(url_for('immobili'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM immobili WHERE id = %s', (id,))
        immobile = cursor.fetchone()
        
        if immobile is None:
            flash('Immobile non trovato!', 'error')
            return redirect(url_for('immobili'))
        
        return render_template('modifica_immobile.html', immobile=immobile)
        
    except Error as e:
        flash(f'Errore nel recupero dell\'immobile: {e}', 'error')
        return redirect(url_for('immobili'))
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/salva_immobile', methods=['POST'])
def salva_immobile():
    """Salva un immobile (nuovo o modificato) nel database"""
    # Recupera i dati dal form
    id_immobile = request.form.get('id')
    indirizzo = request.form['indirizzo']
    citta = request.form['citta']
    prezzo = float(request.form['prezzo'])
    metratura = int(request.form['metratura'])
    descrizione = request.form['descrizione']
    disponibile = 1 if 'disponibile' in request.form else 0
    
    conn = get_db_connection()
    if conn is None:
        flash('Errore di connessione al database!', 'error')
        return redirect(url_for('immobili'))
    
    try:
        cursor = conn.cursor()
        
        if id_immobile:  # Modifica immobile esistente
            cursor.execute('''
                UPDATE immobili 
                SET indirizzo = %s, citta = %s, prezzo = %s, metratura = %s, 
                    descrizione = %s, disponibile = %s
                WHERE id = %s
            ''', (indirizzo, citta, prezzo, metratura, descrizione, disponibile, id_immobile))
            flash('Immobile modificato con successo!', 'success')
        else:  # Nuovo immobile
            cursor.execute('''
                INSERT INTO immobili (indirizzo, citta, prezzo, metratura, descrizione, disponibile)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (indirizzo, citta, prezzo, metratura, descrizione, disponibile))
            flash('Immobile aggiunto con successo!', 'success')
        
        conn.commit()
        
    except Error as e:
        flash(f'Errore nel salvataggio dell\'immobile: {e}', 'error')
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
    
    return redirect(url_for('immobili'))

@app.route('/elimina_immobile/<int:id>')
def elimina_immobile(id):
    """Elimina un immobile dal database"""
    conn = get_db_connection()
    if conn is None:
        flash('Errore di connessione al database!', 'error')
        return redirect(url_for('immobili'))
    
    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM immobili WHERE id = %s', (id,))
        conn.commit()
        flash('Immobile eliminato con successo!', 'success')
        
    except Error as e:
        flash(f'Errore nell\'eliminazione dell\'immobile: {e}', 'error')
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
    
    return redirect(url_for('immobili'))

# GESTIONE CLIENTI

@app.route('/clienti')
def clienti():
    """Visualizza la lista di tutti i clienti"""
    conn = get_db_connection()
    if conn is None:
        flash('Errore di connessione al database!', 'error')
        return render_template('clienti.html', clienti=[])
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM clienti ORDER BY cognome, nome')
        clienti = cursor.fetchall()
        return render_template('clienti.html', clienti=clienti)
        
    except Error as e:
        flash(f'Errore nel recupero dei clienti: {e}', 'error')
        return render_template('clienti.html', clienti=[])
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/aggiungi_cliente')
def aggiungi_cliente():
    """Mostra il form per aggiungere un nuovo cliente"""
    return render_template('modifica_cliente.html', cliente=None)

@app.route('/modifica_cliente/<int:id>')
def modifica_cliente(id):
    """Mostra il form per modificare un cliente esistente"""
    conn = get_db_connection()
    if conn is None:
        flash('Errore di connessione al database!', 'error')
        return redirect(url_for('clienti'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM clienti WHERE id = %s', (id,))
        cliente = cursor.fetchone()
        
        if cliente is None:
            flash('Cliente non trovato!', 'error')
            return redirect(url_for('clienti'))
        
        return render_template('modifica_cliente.html', cliente=cliente)
        
    except Error as e:
        flash(f'Errore nel recupero del cliente: {e}', 'error')
        return redirect(url_for('clienti'))
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/salva_cliente', methods=['POST'])
def salva_cliente():
    """Salva un cliente (nuovo o modificato) nel database"""
    # Recupera i dati dal form
    id_cliente = request.form.get('id')
    nome = request.form['nome']
    cognome = request.form['cognome']
    email = request.form['email']
    telefono = request.form['telefono']
    
    conn = get_db_connection()
    if conn is None:
        flash('Errore di connessione al database!', 'error')
        return redirect(url_for('clienti'))
    
    try:
        cursor = conn.cursor()
        
        if id_cliente:  # Modifica cliente esistente
            cursor.execute('''
                UPDATE clienti 
                SET nome = %s, cognome = %s, email = %s, telefono = %s
                WHERE id = %s
            ''', (nome, cognome, email, telefono, id_cliente))
            flash('Cliente modificato con successo!', 'success')
        else:  # Nuovo cliente
            cursor.execute('''
                INSERT INTO clienti (nome, cognome, email, telefono)
                VALUES (%s, %s, %s, %s)
            ''', (nome, cognome, email, telefono))
            flash('Cliente aggiunto con successo!', 'success')
        
        conn.commit()
        
    except Error as e:
        if e.errno == 1062:  # Errore di duplicazione (email già esistente)
            flash('Errore: Email già esistente nel database!', 'error')
        else:
            flash(f'Errore nel salvataggio del cliente: {e}', 'error')
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
    
    return redirect(url_for('clienti'))

@app.route('/elimina_cliente/<int:id>')
def elimina_cliente(id):
    """Elimina un cliente dal database"""
    conn = get_db_connection()
    if conn is None:
        flash('Errore di connessione al database!', 'error')
        return redirect(url_for('clienti'))
    
    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM clienti WHERE id = %s', (id,))
        conn.commit()
        flash('Cliente eliminato con successo!', 'success')
        
    except Error as e:
        flash(f'Errore nell\'eliminazione del cliente: {e}', 'error')
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
    
    return redirect(url_for('clienti'))

# Route per testare la connessione al database
@app.route('/test_connection')
def test_connection():
    """Route per testare la connessione al database (utile per debug)"""
    conn = get_db_connection()
    if conn is None:
        return "❌ Connessione al database fallita!"
    else:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            return f"✅ Connessione riuscita! MySQL versione: {version}"
        except Error as e:
            return f"❌ Errore: {e}"
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

if __name__ == '__main__':
    # Carica la configurazione del database
    load_db_config()
    
    # Verifica che tutti i parametri necessari siano presenti
    required_keys = ['HOST', 'PORT', 'DATABASE', 'USERNAME', 'PASSWORD']
    missing_keys = [key for key in required_keys if key not in DB_CONFIG]
    
    if missing_keys:
        print(f"ERRORE: Parametri mancanti nel file connessione.txt: {missing_keys}")
        exit(1)
    
    # Inizializza il database al primo avvio
    if init_database():
        print("✅ Database inizializzato correttamente!")
        print(f"🌐 Connesso a MySQL su {DB_CONFIG['HOST']}:{DB_CONFIG['PORT']}")
        print(f"📊 Database: {DB_CONFIG['DATABASE']}")
        print("🚀 Avvio dell'applicazione Flask...")
        
        # Avvia l'applicazione Flask in modalità debug
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        print("❌ Impossibile inizializzare il database. Controlla la configurazione.")
        print("💡 Visita http://localhost:5000/test_connection per testare la connessione")