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
    """Verifica la connessione al database esistente"""
    conn = get_db_connection()
    if conn is None:
        print("Impossibile connettersi al database!")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Verifica che le tabelle esistano nel database agenzia_immobiliare
        cursor.execute("SHOW TABLES LIKE 'dbSistImm_Clienti'")
        clienti_table = cursor.fetchone()
        
        cursor.execute("SHOW TABLES LIKE 'dbSistImm_Immobili'")
        immobili_table = cursor.fetchone()
        
        if not clienti_table or not immobili_table:
            print("Errore: Le tabelle richieste non sono presenti nel database!")
            return False
            
        print("Database verificato con successo!")
        return True
        
    except Error as e:
        print(f"Errore durante la verifica del database: {e}")
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
        cursor.execute('SELECT COUNT(*) FROM dbSistImm_Immobili')
        immobili_totali = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM dbSistImm_Immobili WHERE stato = "Disponibile"')
        immobili_disponibili = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM dbSistImm_Clienti')
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
    # Recupera i parametri di ricerca
    search_query = request.args.get('search', '').strip()
    
    conn = get_db_connection()
    if conn is None:
        flash('Errore di connessione al database!', 'error')
        return render_template('immobili.html', immobili=[], search_query=search_query)
    
    try:
        cursor = conn.cursor(dictionary=True)  # Restituisce risultati come dizionari
        
        if search_query:
            # Query di ricerca
            search_pattern = f"%{search_query}%"
            cursor.execute('''
                SELECT i.codice as id, i.indirizzo, i.civico, i.citta, i.zona, i.tipologia, 
                       i.metratura, i.anno_incarico, i.stato as disponibile, i.note as descrizione,
                       c.cognome as cliente_cognome, c.nome as cliente_nome
                FROM dbSistImm_Immobili i
                LEFT JOIN dbSistImm_Clienti c ON i.id_cliente = c.id_cliente
                WHERE i.codice LIKE %s 
                   OR i.indirizzo LIKE %s 
                   OR i.citta LIKE %s 
                   OR i.zona LIKE %s 
                   OR c.cognome LIKE %s 
                   OR c.nome LIKE %s
                ORDER BY i.codice DESC
            ''', (search_pattern, search_pattern, search_pattern, search_pattern, search_pattern, search_pattern))
        else:
            # Query normale senza ricerca
            cursor.execute('''
                SELECT i.codice as id, i.indirizzo, i.civico, i.citta, i.zona, i.tipologia, 
                       i.metratura, i.anno_incarico, i.stato as disponibile, i.note as descrizione,
                       c.cognome as cliente_cognome, c.nome as cliente_nome
                FROM dbSistImm_Immobili i
                LEFT JOIN dbSistImm_Clienti c ON i.id_cliente = c.id_cliente
                ORDER BY i.codice DESC
            ''')
        
        immobili = cursor.fetchall()
        return render_template('immobili.html', immobili=immobili, search_query=search_query)
        
    except Error as e:
        flash(f'Errore nel recupero degli immobili: {e}', 'error')
        return render_template('immobili.html', immobili=[], search_query=search_query)
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/aggiungi_immobile')
def aggiungi_immobile():
    """Mostra il form per aggiungere un nuovo immobile"""
    conn = get_db_connection()
    if conn is None:
        flash('Errore di connessione al database!', 'error')
        return render_template('modifica_immobile.html', immobile=None, clienti=[])
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT id_cliente, cognome, nome FROM dbSistImm_Clienti ORDER BY cognome, nome')
        clienti = cursor.fetchall()
        return render_template('modifica_immobile.html', immobile=None, clienti=clienti)
        
    except Error as e:
        flash(f'Errore nel recupero dei clienti: {e}', 'error')
        return render_template('modifica_immobile.html', immobile=None, clienti=[])
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/modifica_immobile/<string:id>')
def modifica_immobile(id):
    """Mostra il form per modificare un immobile esistente"""
    conn = get_db_connection()
    if conn is None:
        flash('Errore di connessione al database!', 'error')
        return redirect(url_for('immobili'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT codice as id, indirizzo, civico, citta, zona, tipologia, metratura, anno_incarico, stato as disponibile, note as descrizione, id_cliente FROM dbSistImm_Immobili WHERE codice = %s', (id,))
        immobile = cursor.fetchone()
        
        if immobile is None:
            flash('Immobile non trovato!', 'error')
            return redirect(url_for('immobili'))
        
        # Recupera la lista dei clienti per il dropdown
        cursor.execute('SELECT id_cliente, cognome, nome FROM dbSistImm_Clienti ORDER BY cognome, nome')
        clienti = cursor.fetchall()
        
        return render_template('modifica_immobile.html', immobile=immobile, clienti=clienti)
        
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
    civico = request.form.get('civico', '') or None
    citta = request.form['citta']
    zona = request.form.get('zona', '') or None
    tipologia = request.form.get('tipologia', 'Abitativo')
    metratura = float(request.form.get('metratura', 0)) if request.form.get('metratura') else None
    anno_incarico = request.form.get('anno_incarico', None)
    stato = request.form.get('stato', 'Attivo')
    descrizione = request.form.get('descrizione', '') or None
    id_cliente = request.form.get('id_cliente', '') or None
    
    # Convert empty string to None for id_cliente to avoid foreign key constraint issues
    if id_cliente == '':
        id_cliente = None
    
    conn = get_db_connection()
    if conn is None:
        flash('Errore di connessione al database!', 'error')
        return redirect(url_for('immobili'))
    
    try:
        cursor = conn.cursor()
        
        if id_immobile and id_immobile != 'Generato automaticamente':  # Modifica immobile esistente
            cursor.execute('''
                UPDATE dbSistImm_Immobili 
                SET indirizzo = %s, civico = %s, citta = %s, zona = %s, 
                    tipologia = %s, metratura = %s, anno_incarico = %s, 
                    stato = %s, note = %s, id_cliente = %s
                WHERE codice = %s
            ''', (indirizzo, civico, citta, zona, tipologia, metratura, anno_incarico, stato, descrizione, id_cliente, id_immobile))
            flash('Immobile modificato con successo!', 'success')
        else:  # Nuovo immobile
            # Genera un nuovo codice per l'immobile nel formato SInnnn
            cursor.execute("SELECT MAX(CAST(SUBSTRING(codice, 3) AS UNSIGNED)) FROM dbSistImm_Immobili WHERE codice LIKE 'SI%'")
            result = cursor.fetchone()
            max_num = result[0] if result[0] is not None else 0
            nuovo_numero = max_num + 1
            nuovo_codice = f"SI{nuovo_numero:04d}"
            
            cursor.execute('''
                INSERT INTO dbSistImm_Immobili (codice, indirizzo, civico, citta, zona, 
                    tipologia, metratura, anno_incarico, stato, note, id_cliente)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (nuovo_codice, indirizzo, civico, citta, zona, tipologia, metratura, anno_incarico, stato, descrizione, id_cliente))
            flash('Immobile aggiunto con successo!', 'success')
        
        conn.commit()
        
    except Error as e:
        flash(f'Errore nel salvataggio dell\'immobile: {e}', 'error')
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
    
    return redirect(url_for('immobili'))

@app.route('/elimina_immobile/<string:id>')
def elimina_immobile(id):
    """Elimina un immobile dal database"""
    conn = get_db_connection()
    if conn is None:
        flash('Errore di connessione al database!', 'error')
        return redirect(url_for('immobili'))
    
    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM dbSistImm_Immobili WHERE codice = %s', (id,))
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
    # Recupera i parametri di ricerca
    search_query = request.args.get('search', '').strip()
    
    conn = get_db_connection()
    if conn is None:
        flash('Errore di connessione al database!', 'error')
        return render_template('clienti.html', clienti=[], search_query=search_query)
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        if search_query:
            # Query di ricerca
            search_pattern = f"%{search_query}%"
            cursor.execute('''
                SELECT id_cliente, cognome, nome, codice_fiscale, partita_iva, telefono, email, indirizzo, citta, cap 
                FROM dbSistImm_Clienti 
                WHERE id_cliente LIKE %s 
                   OR cognome LIKE %s 
                   OR nome LIKE %s 
                   OR codice_fiscale LIKE %s 
                   OR partita_iva LIKE %s 
                   OR telefono LIKE %s 
                   OR email LIKE %s 
                   OR indirizzo LIKE %s 
                   OR citta LIKE %s
                ORDER BY cognome, nome
            ''', (search_pattern, search_pattern, search_pattern, search_pattern, search_pattern, search_pattern, search_pattern, search_pattern, search_pattern))
        else:
            # Query normale senza ricerca
            cursor.execute('SELECT id_cliente, cognome, nome, codice_fiscale, partita_iva, telefono, email, indirizzo, citta, cap FROM dbSistImm_Clienti ORDER BY cognome, nome')
        
        clienti = cursor.fetchall()
        return render_template('clienti.html', clienti=clienti, search_query=search_query)
        
    except Error as e:
        flash(f'Errore nel recupero dei clienti: {e}', 'error')
        return render_template('clienti.html', clienti=[], search_query=search_query)
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
        cursor.execute('SELECT id_cliente, cognome, nome, codice_fiscale, partita_iva, telefono, email, indirizzo, citta, cap, note FROM dbSistImm_Clienti WHERE id_cliente = %s', (id,))
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
    codice_fiscale = request.form.get('codice_fiscale', '') or None
    partita_iva = request.form.get('partita_iva', '') or None
    telefono = request.form.get('telefono', '') or None
    email = request.form.get('email', '') or None
    indirizzo = request.form.get('indirizzo', '') or None
    citta = request.form.get('citta', '') or None
    cap = request.form.get('cap', '') or None
    note = request.form.get('note', '') or None
    
    conn = get_db_connection()
    if conn is None:
        flash('Errore di connessione al database!', 'error')
        return redirect(url_for('clienti'))
    
    try:
        cursor = conn.cursor()
        
        if id_cliente:  # Modifica cliente esistente
            cursor.execute('''
                UPDATE dbSistImm_Clienti 
                SET nome = %s, cognome = %s, codice_fiscale = %s, partita_iva = %s, 
                    telefono = %s, email = %s, indirizzo = %s, citta = %s, cap = %s, note = %s
                WHERE id_cliente = %s
            ''', (nome, cognome, codice_fiscale, partita_iva, telefono, email, indirizzo, citta, cap, note, id_cliente))
            flash('Cliente modificato con successo!', 'success')
        else:  # Nuovo cliente
            # Genera il nuovo id_cliente nel formato SICnnnn
            cursor.execute("SELECT MAX(CAST(SUBSTRING(id_cliente, 4) AS UNSIGNED)) FROM dbSistImm_Clienti WHERE id_cliente LIKE 'SIC%'")
            max_num = cursor.fetchone()[0]
            nuovo_numero = (max_num or 0) + 1
            nuovo_id_cliente = f"SIC{nuovo_numero:04d}"
            
            cursor.execute('''
                INSERT INTO dbSistImm_Clienti (id_cliente, nome, cognome, codice_fiscale, partita_iva, 
                    telefono, email, indirizzo, citta, cap, note)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (nuovo_id_cliente, nome, cognome, codice_fiscale, partita_iva, telefono, email, indirizzo, citta, cap, note))
            flash('Cliente aggiunto con successo!', 'success')
        
        conn.commit()
        
    except Error as e:
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
        cursor.execute('DELETE FROM dbSistImm_Clienti WHERE id_cliente = %s', (id,))
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
        # host='0.0.0.0' permette connessioni da qualsiasi indirizzo IP
        app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
    else:
        print("❌ Impossibile inizializzare il database. Controlla la configurazione.")
        print("💡 Visita http://localhost:5000/test_connection per testare la connessione")