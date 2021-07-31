'''
Note per la prima creazione del database:
1. Aprire una console python tramite il comando
    heroku run python
2. Dare il comando
    from server_arduino import db
3. Dare il comando #Praticamente crea le tabelle sulla base di come sono state dichiarate nello script server_arduino.py
    db.create_all()
4. Chiudere il terminale con il comando
    quit()
5. Riavviare Heroku tramite il comando
    heroku restart
'''


# Import delle librerie necessarie
import logging
import os
import json

from queue import Queue                 # Queue server la gestione della multiutenza del bot
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, Dispatcher

from flask import Flask                 # Usero' questa classe per creare l'applicazione
from flask_sqlalchemy import SQLAlchemy # Usero' questa classe per il database
from flask import request               # Usero' request per maneggiare le richieste esterne

from datetime import datetime, timedelta



############# FIX BUG DI HEROKU #############
# Il bug è relativo ad una variabile di sistema che heroku usa, ma che SQLAlchemy non supporta piu'
import re
database_uri = os.getenv("DATABASE_URL")  # or other relevant config var
if database_uri.startswith("postgres://"):
    database_uri = database_uri.replace("postgres://", "postgresql://", 1)
# Per usare la connessione al database, utilizzare la stringa "database_uri"
#############################################

# Informazioni hardcoded necessarie per il funzionamento di FLASK  e del WebHook telegram
PORT = int(os.environ.get('PORT', '443'))
TOKEN = '1839283874:AAGl-KUiV5zBIlMivmWfn-FVkg7mWgwE_us'
HEROKU_APP_ADDRESS = 'https://asd-care-server.herokuapp.com/'

# Fuso orario per gestire i timestamp inviati/rivecuti dalla Node-MCU
GMT = 2

# Informazioni necessarie all'uso di PostgreSQL
proprietario_database = "postgres"
password_database = "gianfranco"
host_database = "localhost:5432"
nome_database = "Database_ASDCARE"

# Oggeti necessari per l'handling dei messaggi ricevuti ed inviati dal Bot
bot = Bot(TOKEN)
update_queue = Queue()
dispatcher_del_bot = Dispatcher(bot, update_queue)

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)







################################################################################
# Funzioni utili nel programma:

#######################################
# CHECK IF USER EXIST (DATABASE MODE):
def check_user(user_id):
    # Messaggio di servizio
    print("Check sull'utente ", user_id, "...\n")

    # Controllo che nel database esista l'utente
    stringa = str(user_id)
    exists = db.session.query(db.exists().where(ElencoUtenti.identificativo == stringa)).scalar()
    db.session.close()

    if exists:
        print("Il codice utente ", user_id, " e' stato trovato\n")
        return True  # Si nel file? Allora TRUE
    else :
        print("Il codice utente ", user_id, " non e' stato trovato\n")
        return False # Non ci sei? Allora FALSE



#######################################
# RECUPERO INFORMAZIONI TEMPO:
def recupero_tempo_GMT():
    # Recupero il reale tempo del mondo con GMT = 0
    UTC_time = datetime.utcnow()

    # Aggiungo le ore GMT per traslare il tempo al GMT locale
    hours_to_be_added = timedelta(hours = GMT)

    # Restituisce il timestampo corretto
    return (UTC_time + hours_to_be_added)



#######################################
# UPDATE LAST USER COMMAND ON DATABASE:
def update_last_command(user_id, message):
    # Messaggio di servizio
    print("Update dell'ultimo comando inserito da ", user_id, " con ", message, "...\n")

    # Query che serve per fare l'update della riga corrispondente all'utente nel database
    stringa_user = str(user_id)
    stringa_messaggio = str(message)
    db.session.query(ElencoUtenti).filter(ElencoUtenti.identificativo == stringa_user).update({ElencoUtenti.last_command: stringa_messaggio})
    db.session.commit()
    db.session.close()



#######################################
# UPDATE LAST USER COMMAND ON DATABASE:
def check_last_command(user_id):
    # Messaggio di servizio
    print("Ricerca dell'ultimo comando inserito da ", user_id, "...\n")

    # Query che serve per recuperare l'ultimo comando inserito dall'utente
    stringa_user = str(user_id)
    query_0 = db.session.query(ElencoUtenti).filter(ElencoUtenti.identificativo == stringa_user)
    sub_query_1 = query_0.first()
    db.session.close()

    # Messaggio di servizio
    print(sub_query_1.last_command)

    # Restituisce l'ultimo comando inserito dall'utente al chiamante
    return str(sub_query_1.last_command)



#######################################
# UPDATE LAST USER COMMAND ON DATABASE:
def is_valid_decimal(stringa_numerica):     # Controlla se la stringa e' solo numerica (intera o decimale)
    try:
        float(stringa_numerica)
    except ValueError:
        return False
    else:
        return True







################################################################################
# Funzionalita' del Bot Telegram

#######################################
# START:
def start(update, context):
    # Raccolta info del nuovo user
    identificativo_utente = update.message.chat_id
    nome_utente = update.message.chat.first_name
    cognome_utente = update.message.chat.last_name
    nickname_utente = update.message.chat.username
    testo_utente = update.message.text
    update.message.reply_text('Bot successfully started!')

    # Greetings
    context.bot.send_message(chat_id=identificativo_utente, text="Buongiorno {}!".format(nome_utente))

    # Messaggio di servizio
    print("E' stata effettuato un accesso al bot\n   chat_id : {} and firstname : {} lastname : {}  username {}".format(identificativo_utente, nome_utente, cognome_utente, nickname_utente))

    # Check se esiste gia' l'utente nel server
    if(check_user(identificativo_utente) == False):
        context.bot.send_message(chat_id=identificativo_utente,
                                 text="Sembri nuovo da queste parti! Ti puoi registrare con /new_user\n"
                                      "Qualora invece volessi eliminare il tuo utente, digita /delete_user\n"
                                      "Per vedere l'utlima occorrenza, digita /last_alarm\n"
                                      "Per vedere l'intero log delle occorrenze, digita /log_alarms\n"
                                      "Per veder le occorrenze dell'ultima giornata, digita /last_day\n"
                                      "Per vedere le occorrenze nell'ultimo mese, digita /last_month\n"
                                      "Per vedere il totale degli episodi occorsi nell'ultimo anno, digita /last_year\n"
                                      "Per modificare i parametri di sensibilita', digita /modifica_sensibilita\n"
                                      "Per rivedere la lista dei comandi, digita /help\n")
    else:
        context.bot.send_message(chat_id= identificativo_utente, text= "Sei gia' nella lista utenti registrati, sei pronto ad usare il servizio")
        update_last_command(identificativo_utente, testo_utente)

    update_last_command(identificativo_utente, testo_utente)



#######################################
# NEW_USER:
def new_user(update, context):
    # Raccolta info del nuovo user
    identificativo_utente = update.message.chat_id
    nome_utente = update.message.chat.first_name
    cognome_utente = update.message.chat.last_name
    nickname_utente = update.message.chat.username
    testo_utente = update.message.text
    update.message.reply_text('Ora vediamo di aggiungerti! Un attimo solo...')

    # Check se esiste gia' l'utente nel server
    if(check_user(identificativo_utente) == False):
        # Messaggio di servizio
        print("Utente da aggiungere:\n   chat_id : {} and firstname : {} lastname : {}  username {}".format(identificativo_utente, nome_utente, cognome_utente, nickname_utente))

        # Messaggio di servizio su Telegram
        context.bot.send_message(chat_id=identificativo_utente, text="Ancora un attimo...")

        # Creo la nuova riga da aggiungere al database e poi ne faccio il commit
        nuovo_utente = ElencoUtenti(identificativo=identificativo_utente, nome=nome_utente, cognome=cognome_utente, nickname=nickname_utente, soglia_modulo=1.5, soglia_durata=2, last_command="/new_user")
        db.session.add(nuovo_utente)
        db.session.commit()
        db.session.close()

        # Messaggio di servizio su Telegram
        context.bot.send_message(chat_id=identificativo_utente, text="Ecco fatto, ora sei dei nostri!\nBenvenuta/o =)")
        context.bot.send_message(chat_id=identificativo_utente, text="Per utilizzare il servizio, il tuo codice utente sara':\n{}".format(identificativo_utente))

    else:
        # L'utente era gia' registrato. Lo avviso
        context.bot.send_message(chat_id= identificativo_utente, text= "Che sciocco, non ti avevo riconosciuto. Eri gia' in cima alla lista delle belle persone!")
        context.bot.send_message(chat_id=identificativo_utente, text="Ti ricordo che il codice utente per utilizzare il servizio e':\n{}".format(identificativo_utente))
        update_last_command(identificativo_utente, testo_utente)



#######################################
# DELETE USER:
def delete_user(update, context):
    # Raccolta info del nuovo user
    identificativo_utente = update.message.chat_id
    nome_utente = update.message.chat.first_name
    cognome_utente = update.message.chat.last_name
    nickname_utente = update.message.chat.username
    testo_utente = update.message.text
    update.message.reply_text('Ci dispiace che vada via! Un attimo solo...')

    # Check se esiste gia' l'utente nel server
    if (check_user(identificativo_utente) == True):
        # Messaggio di servizio
        print("Utente da rimuovere:\n   chat_id : {} and firstname : {} lastname : {}  username {}".format(identificativo_utente, nome_utente, cognome_utente, nickname_utente))

        # Messaggio di servizio su Telegram
        context.bot.send_message(chat_id=identificativo_utente, text="Ancora un attimo...")

        # Pulire tabella User
        utente_da_cancellare = ElencoUtenti.__table__.delete().where(ElencoUtenti.identificativo == str(identificativo_utente))
        db.session.execute(utente_da_cancellare)
        # Pulire tabella Log
        utente_da_cancellare = LogOccorrenze.__table__.delete().where(LogOccorrenze.identificativo == str(identificativo_utente))
        db.session.execute(utente_da_cancellare)
        db.session.commit()
        db.session.close()

        # Messaggio di servizio su Telegram
        context.bot.send_message(chat_id=identificativo_utente,
                                 text="Speriamo tornerai presto a trovarci!\nArrivederci =)")
    else:
        context.bot.send_message(chat_id=identificativo_utente,
                                 text="Mi hai chiesto di cancellarti, ma sembra che gia' non fossi dei nostri... Puoi unirti con /new_user")



#######################################
# LAST ALARM:
def last_alarm(update, context):
    # Raccolta info del nuovo user
    identificativo_utente = update.message.chat_id
    nome_utente = update.message.chat.first_name
    cognome_utente = update.message.chat.last_name
    nickname_utente = update.message.chat.username
    testo_utente = update.message.text
    update.message.reply_text('Ora controlliamo. Attendi un attimo...')

    # Check se esiste gia' l'utente nel server
    if (check_user(identificativo_utente) == True):
        # Messaggio di servizio
        print("Servzio chiesto da:\n   chat_id : {} and firstname : {} lastname : {}  username {}".format(identificativo_utente, nome_utente, cognome_utente, nickname_utente))

        # Messaggio di servizio su Telegram
        context.bot.send_message(chat_id=identificativo_utente, text="Ancora un attimo...")

        # Cerco l'ultima chiave relativa all'utente caratterizzato da identificativo
        query_0 = db.session.query(LogOccorrenze)
        sub_query_1 = query_0.filter(LogOccorrenze.identificativo == str(identificativo_utente), LogOccorrenze.allarme == 2)
        sub_query_2 = sub_query_1.order_by(LogOccorrenze.etichetta_tempo.desc()).first() #desc server per ordinare descending la colonna indicata
        db.session.close()

        # Messaggio di servizio
        print(sub_query_2)
        print(type(sub_query_2))

        if sub_query_2 is not None : #None serve solo in questo caso, negli altri bisogna controllare che la risposta abbia count diverso da 0
            # Messaggio di servizio e risposta
            print(sub_query_2.etichetta_tempo)
            context.bot.send_message(chat_id=identificativo_utente, text="L'ultima occorrenza si è verificata in data:\n {}".format(sub_query_2.etichetta_tempo))
        else:
            context.bot.send_message(chat_id=identificativo_utente, text="Non si sono ancora verificate occorrenze\n")

        update_last_command(identificativo_utente, testo_utente)

    else:
        # L'utente era gia' registrato. Lo avviso
        context.bot.send_message(chat_id=identificativo_utente, text="Sembra che ancora tu non sia dei nostri... Puoi unirti con /new_user")



#######################################
# LOG ALARMS:
def log_alarms(update, context):
    # Raccolta info del nuovo user
    identificativo_utente = update.message.chat_id
    nome_utente = update.message.chat.first_name
    cognome_utente = update.message.chat.last_name
    nickname_utente = update.message.chat.username
    testo_utente = update.message.text
    update.message.reply_text('Ora controlliamo. Attendi un attimo...')

    # Check se esiste gia' l'utente nel server
    if (check_user(identificativo_utente) == True):
        # Messaggio di servizio
        print("Servzio chiesto da:\n   chat_id : {} and firstname : {} lastname : {}  username {}".format(identificativo_utente, nome_utente, cognome_utente, nickname_utente))

        # Messaggio di servizio su Telegram
        context.bot.send_message(chat_id=identificativo_utente, text="Ancora un attimo...")

        # Cerco la chiave relativa all'utente caratterizzato da identificativo
        query_0 = db.session.query(LogOccorrenze.etichetta_tempo)
        sub_query_1 = query_0.filter(LogOccorrenze.identificativo == str(identificativo_utente), LogOccorrenze.allarme == 2)
        sub_query_2 = sub_query_1.order_by(LogOccorrenze.etichetta_tempo.desc()) #desc server per ordinare descending la colonna indicata
        db.session.close()

        #print(sub_query_2)
        #print(type(sub_query_2))

        if sub_query_2.count() != 0 :
            stringa = str()
            # Spacchetto il risultato della query
            for row in sub_query_2:
                stringa += str(row.etichetta_tempo) + "\n "
            print(stringa)
            context.bot.send_message(chat_id=identificativo_utente, text="Il log delle occorrenze che si sono verificate e' il seguente:\n {}".format(stringa))
        else:
            context.bot.send_message(chat_id=identificativo_utente, text="Non si sono ancora verificate occorrenze\n")

        update_last_command(identificativo_utente, testo_utente)

    else:
        # L'utente era gia' registrato. Lo avviso
        context.bot.send_message(chat_id=identificativo_utente, text="Sembra che ancora tu non sia dei nostri... Puoi unirti con /new_user")



#######################################
# LAST DAY:
def last_day(update, context):
    # Raccolta info del nuovo user
    identificativo_utente = update.message.chat_id
    nome_utente = update.message.chat.first_name
    cognome_utente = update.message.chat.last_name
    nickname_utente = update.message.chat.username
    testo_utente = update.message.text
    update.message.reply_text('Ora controlliamo. Attendi un attimo...')

    # Check se esiste gia' l'utente nel server
    if (check_user(identificativo_utente) == True):
        # Messaggio di servizio
        print("Servzio chiesto da:\n   chat_id : {} and firstname : {} lastname : {}  username {}".format(identificativo_utente, nome_utente, cognome_utente, nickname_utente))

        # Messaggio di servizio su Telegram
        context.bot.send_message(chat_id=identificativo_utente, text="Ancora un attimo...")

        # Calcolo la data del passato
        GMT_time = recupero_tempo_GMT()
        passato = GMT_time - timedelta(days=1)
        contatore_occorrenze = 0

        # Cerco la chiave relativa all'utente caratterizzato da identificativo
        query_0 = db.session.query(LogOccorrenze.etichetta_tempo)
        sub_query_1 = query_0.filter(LogOccorrenze.identificativo == str(identificativo_utente), LogOccorrenze.allarme == 2)
        sub_query_2 = sub_query_1.order_by(LogOccorrenze.etichetta_tempo.desc())  # desc server per ordinare descending la colonna indicata
        sub_query_3 = sub_query_2.filter(LogOccorrenze.etichetta_tempo >= passato)
        # Contiamo le occorrenze
        contatore_occorrenze = sub_query_3.count()
        db.session.close()

        if sub_query_3.count() != 0 :
            stringa = str()
            # Spacchetto il risultato della query
            for row in sub_query_3:
                stringa += str(row.etichetta_tempo) + "\n "
            print(stringa)
            context.bot.send_message(chat_id=identificativo_utente, text="Durante questo ultimo giorno si sono verificate {} occorrenze. Il log e':\n {}".format(contatore_occorrenze, stringa))
        else:
            context.bot.send_message(chat_id=identificativo_utente, text="Non si sono ancora verificate occorrenze\n")

        update_last_command(identificativo_utente, testo_utente)

    else:
        # L'utente era gia' registrato. Lo avviso
        context.bot.send_message(chat_id=identificativo_utente, text="Sembra che ancora tu non sia dei nostri... Puoi unirti con /new_user")



#######################################
# LAST MONTH:
def last_month(update, context):
    # Raccolta info del nuovo user
    identificativo_utente = update.message.chat_id
    nome_utente = update.message.chat.first_name
    cognome_utente = update.message.chat.last_name
    nickname_utente = update.message.chat.username
    testo_utente = update.message.text
    update.message.reply_text('Ora controlliamo. Attendi un attimo...')

    # Check se esiste gia' l'utente nel server
    if (check_user(identificativo_utente) == True):
        # Messaggio di servizio
        print("Servzio chiesto da:\n   chat_id : {} and firstname : {} lastname : {}  username {}".format(identificativo_utente, nome_utente, cognome_utente, nickname_utente))

        # Messaggio di servizio su Telegram
        context.bot.send_message(chat_id=identificativo_utente, text="Ancora un attimo...")

        # Calcolo la data del passato
        GMT_time = recupero_tempo_GMT()
        passato = GMT_time - timedelta(days=30)
        contatore_occorrenze = 0

        # Cerco la chiave relativa all'utente caratterizzato da identificativo
        query_0 = db.session.query(LogOccorrenze.etichetta_tempo)
        sub_query_1 = query_0.filter(LogOccorrenze.identificativo == str(identificativo_utente), LogOccorrenze.allarme == 2)
        sub_query_2 = sub_query_1.order_by(LogOccorrenze.etichetta_tempo.desc())  # desc server per ordinare descending la colonna indicata
        sub_query_3 = sub_query_2.filter(LogOccorrenze.etichetta_tempo >= passato)
        # Contiamo le occorrenze
        contatore_occorrenze = sub_query_3.count()
        db.session.close()

        if sub_query_3.count() != 0 :
            stringa = str()
            # Spacchetto il risultato della query
            for row in sub_query_3:
                stringa += str(row.etichetta_tempo) + "\n "
                print(stringa)
            context.bot.send_message(chat_id=identificativo_utente, text="Durante questo ultimo mese si sono verificate {} occorrenze. Il log e':\n {}".format(contatore_occorrenze, stringa))
        else:
            context.bot.send_message(chat_id=identificativo_utente, text="Non si sono ancora verificate occorrenze\n")

        update_last_command(identificativo_utente, testo_utente)

    else:
        # L'utente era gia' registrato. Lo avviso
        context.bot.send_message(chat_id=identificativo_utente, text="Sembra che ancora tu non sia dei nostri... Puoi unirti con /new_user")



#######################################
# LAST YEAR:
def last_year(update, context):
    # Raccolta info del nuovo user
    identificativo_utente = update.message.chat_id
    nome_utente = update.message.chat.first_name
    cognome_utente = update.message.chat.last_name
    nickname_utente = update.message.chat.username
    testo_utente = update.message.text
    update.message.reply_text('Ora controlliamo. Attendi un attimo...')

    # Check se esiste gia' l'utente nel server
    if (check_user(identificativo_utente) == True):
        # Messaggio di servizio
        print("Servzio chiesto da:\n   chat_id : {} and firstname : {} lastname : {}  username {}".format(identificativo_utente, nome_utente, cognome_utente, nickname_utente))

        # Messaggio di servizio su Telegram
        context.bot.send_message(chat_id=identificativo_utente, text="Ancora un attimo...")

        # Calcolo la data del passato
        GMT_time = recupero_tempo_GMT()
        passato = GMT_time - timedelta(days=365)
        contatore_occorrenze = 0

        # Cerco la chiave relativa all'utente caratterizzato da identificativo
        query_0 = db.session.query(LogOccorrenze.etichetta_tempo)
        sub_query_1 = query_0.filter(LogOccorrenze.identificativo == str(identificativo_utente), LogOccorrenze.allarme == 2)
        sub_query_2 = sub_query_1.order_by(LogOccorrenze.etichetta_tempo.desc())  # desc server per ordinare descending la colonna indicata
        sub_query_3 = sub_query_2.filter(LogOccorrenze.etichetta_tempo >= passato)
        # Contiamo le occorrenze
        contatore_occorrenze = sub_query_3.count()
        db.session.close()

        if sub_query_3.count() != 0 :
            stringa = str()
            # Spacchetto il risultato della query
            for row in sub_query_3:
                stringa += str(row.etichetta_tempo) + "\n "
            print(stringa)
            context.bot.send_message(chat_id=identificativo_utente, text="Durante questo ultimo anno si sono verificate {} occorrenze. Il log e':\n {}".format(contatore_occorrenze, stringa))
        else:
            context.bot.send_message(chat_id=identificativo_utente, text="Non si sono ancora verificate occorrenze\n")

        update_last_command(identificativo_utente, testo_utente)

    else:
        # L'utente era gia' registrato. Lo avviso
        context.bot.send_message(chat_id=identificativo_utente, text="Sembra che ancora tu non sia dei nostri... Puoi unirti con /new_user")



#######################################
# MODIFICA_SENSIBILITA':
def modifica_sensibilita(update, context):
    # Raccolta info del nuovo user
    identificativo_utente = update.message.chat_id
    nome_utente = update.message.chat.first_name
    cognome_utente = update.message.chat.last_name
    nickname_utente = update.message.chat.username
    testo_utente = update.message.text
    update.message.reply_text('Ora controlliamo. Attendi un attimo...')

    # Check se esiste gia' l'utente nel server
    if (check_user(identificativo_utente) == True):
        # Messaggio di servizio
        print("Servzio chiesto da:\n   chat_id : {} and firstname : {} lastname : {}  username {}".format(identificativo_utente, nome_utente, cognome_utente, nickname_utente))

        # Recupera il vecchio valore
        query_0 = db.session.query(ElencoUtenti.soglia_modulo, ElencoUtenti.soglia_durata)
        sub_query_1 = query_0.filter(ElencoUtenti.identificativo == str(identificativo_utente))
        sub_query_2 = sub_query_1.first()
        db.session.close()

        context.bot.send_message(chat_id=identificativo_utente, text="I vecchi valori erano:\n soglia_modulo: {}\n soglia_durata: {}".format(str(sub_query_2.soglia_modulo),str(sub_query_2.soglia_durata)))
        context.bot.send_message(chat_id=identificativo_utente, text="Invia prima la nuova soglia del modulo e poi"
                                                                     " invia un nuovo messaggio con la nuova soglia della durata\n")
        context.bot.send_message(chat_id=identificativo_utente, text="Inserisci ora la nuova soglia_modulo\n")

        update_last_command(identificativo_utente, testo_utente)

    else:
        # L'utente era gia' registrato. Lo avviso
        context.bot.send_message(chat_id=identificativo_utente, text="Sembra che ancora tu non sia dei nostri... Puoi unirti con /new_user")



#######################################
# FUNZIONI SUPPLEMENTARI:
# def help(update, context):
#     """Send a message when the command /help is issued."""
#     update.message.reply_text('Help!')

# def echo(update, context):
#     """Echo the user message."""
#     update.message.reply_text(update.message.text)
def text_handler(update, context):
    # Raccolta info del nuovo user
    identificativo_utente = update.message.chat_id
    nome_utente = update.message.chat.first_name
    cognome_utente = update.message.chat.last_name
    nickname_utente = update.message.chat.username
    testo_utente = update.message.text

    # Check se esiste gia' l'utente nel server
    if (check_user(identificativo_utente) == True):

        # Se il precedente comando inserito dall'utente era modifica_sensibilita, allora posso prendere il nuovo valore
        if (check_last_command(identificativo_utente) == "/modifica_sensibilita"):      #STEP 1
            stringa_user = str(identificativo_utente)
            stringa_messaggio = str(testo_utente)

            # Controllo che il carattere che l'utente ha passato sia un numero
            if is_valid_decimal(stringa_messaggio):
                # Query che serve per fare l'update della riga corrispondente all'utente nel database
                db.session.query(ElencoUtenti).filter(ElencoUtenti.identificativo == stringa_user).update({ElencoUtenti.soglia_modulo: stringa_messaggio})
                db.session.commit()
                db.session.close()

                context.bot.send_message(chat_id=identificativo_utente, text="soglia_modulo aggiornata correttamente!\n")
                context.bot.send_message(chat_id=identificativo_utente, text="Inserisci ora la nuova soglia_durata\n")
                update_last_command(identificativo_utente, "/modifica_sensibilita_1")
            else:
                context.bot.send_message(chat_id=identificativo_utente, text="Carattere errato! Inserisci un numero intero o decimale (col punto), per favore.\n")
                update_last_command(identificativo_utente, "/modifica_sensibilita")

        elif (check_last_command(identificativo_utente) == "/modifica_sensibilita_1"):  #STEP 2
            stringa_user = str(identificativo_utente)
            stringa_messaggio = str(testo_utente)

            # Controllo che il carattere che l'utente ha passato sia un numero
            if is_valid_decimal(stringa_messaggio):
                # Query che serve per fare l'update della riga corrispondente all'utente nel database
                db.session.query(ElencoUtenti).filter(ElencoUtenti.identificativo == stringa_user).update({ElencoUtenti.soglia_durata: stringa_messaggio})
                db.session.commit()
                db.session.close()

                context.bot.send_message(chat_id=identificativo_utente, text="soglia_durata aggiornata correttamente!\n")
                context.bot.send_message(chat_id=identificativo_utente, text="Modifiche completate.\n")
            else:
                context.bot.send_message(chat_id=identificativo_utente, text="Carattere errato! Inserisci un numero intero o decimale (col punto), per favore.\n")
                update_last_command(identificativo_utente, "/modifica_sensibilita_1")

        else:
            update.message.reply_text('Inserisci uno dei comandi riconosciuti!')

    else:
        # L'utente era gia' registrato. Lo avviso
        context.bot.send_message(chat_id=identificativo_utente, text="Sembra che ancora tu non sia dei nostri... Puoi unirti con /new_user")



#######################################
# HELP:
def help(update, context):
    # Raccolta info del nuovo user
    identificativo_utente = update.message.chat_id
    nome_utente = update.message.chat.first_name
    cognome_utente = update.message.chat.last_name
    nickname_utente = update.message.chat.username
    testo_utente = update.message.text
    update.message.reply_text('La lista dei comandi segue:\n')

    # Risposta all'utente
    context.bot.send_message(chat_id=identificativo_utente,
                             text="Per ricevere il benvenuto, digita /start\n"
                                  "Per registrarti, digita /new_user\n"
                                  "Per eliminare la tua utenza, digita /delete_user\n"
                                  "Per vedere l'utlima occorrenza, digita /last_alarm\n"
                                  "Per vedere l'intero log delle occorrenze, digita /log_alarms\n"
                                  "Per veder le occorrenze dell'ultima giornata, digita /last_day\n"
                                  "Per vedere le occorrenze nell'ultimo mese, digita /last_month\n"
                                  "Per vedere il totale degli episodi occorsi nell'ultimo anno, digita /last_year\n"
                                  "Per modificare i parametri di sensibilita', digita /modifica_sensibilita\n")
    if (check_user(identificativo_utente) == True):
        update_last_command(identificativo_utente, testo_utente)
    else:
        pass



#######################################
# FUNZIONE PER IL LOGGING DI EVENTUALI ERRORI LATO TELEGRAM:
def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)



#######################################
# Decorazione dell'handler dei messaggi di telegram: viene allestito il frontend
# con le funzioni dichiarate sopra:
def bot_setup():
    print("Decorazione del frontend del bot Telegram\n")
    # updater e' il frontend

    # Definizione del comportamento che il bot avra' sulla base dei comandi che ricevera'
    dispatcher_del_bot.add_handler(CommandHandler("start", start))
    dispatcher_del_bot.add_handler(CommandHandler("new_user", new_user))
    dispatcher_del_bot.add_handler(CommandHandler("delete_user", delete_user))
    dispatcher_del_bot.add_handler(CommandHandler("last_alarm", last_alarm))
    dispatcher_del_bot.add_handler(CommandHandler("log_alarms", log_alarms))
    dispatcher_del_bot.add_handler(CommandHandler("last_day", last_day))
    dispatcher_del_bot.add_handler(CommandHandler("last_month", last_month))
    dispatcher_del_bot.add_handler(CommandHandler("last_year", last_year))
    dispatcher_del_bot.add_handler(CommandHandler("last_year", last_year))
    dispatcher_del_bot.add_handler(CommandHandler("modifica_sensibilita", modifica_sensibilita))

    dispatcher_del_bot.add_handler(CommandHandler("help", help))

    # Comportamento rispetto a messaggi "non-comandi"
    dispatcher_del_bot.add_handler(MessageHandler(Filters.text, text_handler))

    # Log di tutti gli errori
    dispatcher_del_bot.add_error_handler(error)



# Esecuzione della decorazione
bot_setup()
print("Checkpoint met safely!\n")







################################################################################
# Funzionalita' del WSGI FLASK

#######################################
# Creo l'applicazione Flask che fungera' da server:
istanza_server = Flask(__name__)

#######################################
# Configuro Flask per usare PostgreSQL e istanzio il database:
# For reference: "postgresql://user:pass@localhost:5432/dbname"
# istanza_server.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://"+ proprietario_database + ":" + password_database + "@" + host_database + "/" + nome_database
istanza_server.config['SQLALCHEMY_DATABASE_URI'] = database_uri
istanza_server.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(istanza_server)

#######################################
# Creo la classi delle tabelle che usero'
class ElencoUtenti(db.Model): #Le classi usano maiuscole senza underscore
    __tablename__ : "elenco_utenti" # ome della vera tabella presente realmente presente sul database
    identificativo = db.Column(db.String(80), primary_key=True)
    nome = db.Column(db.String(80), unique=False, nullable=True)
    cognome = db.Column(db.String(80), unique=False, nullable=True)
    nickname = db.Column(db.String(80), unique=False, nullable=True)
    soglia_modulo = db.Column(db.Float(), unique=False, nullable=False)
    soglia_durata = db.Column(db.Integer(), unique=False, nullable=False)
    last_command = db.Column(db.String(80), unique=False, nullable=False)

class LogOccorrenze(db.Model):
    __tablename__ : "log_occorrenze" # Nome della vera tabella presente realmente presente sul database
    identificativo = db.Column(db.String(80), primary_key=True)
    etichetta_tempo = db.Column(db.DateTime(), primary_key=True)
    accelerazione = db.Column(db.Float(), unique=False, nullable=False)
    asse_x = db.Column(db.Float(), unique=False, nullable=False)
    asse_y = db.Column(db.Float(), unique=False, nullable=False)
    asse_z = db.Column(db.Float(), unique=False, nullable=False)
    allarme = db.Column(db.Integer(), unique=False, nullable=False)



#######################################
# Decorazione dell'applicazione Fask:

###################
# ROOT:
@istanza_server.route('/')
def splash_screen():
    return 'Benvenuto nel cloud ASD Care!\n'



###################
# Handler delle richieste Telegram
@istanza_server.route('/{}'.format(TOKEN), methods=['GET','POST'])
def handler_del_webhook():
    if request.method == "POST":
        # Spacchetto le informazioni ricevute
        update = Update.de_json(request.get_json(force=True), bot)
        chat_id = update.message.chat.id
        msg_id = update.message.message_id
        msg = update.effective_message

        # Messaggio di servizio
        print(msg)
        logger.info('Update received!\n')

        # Passo le informazioni ricevute al dispatcher, che si occuperà di gestirle secondo le funzioni definite
        dispatcher_del_bot.process_update(update)
        update_queue.put(update)

        # Messaggio di servizio
        #update.message.reply_text('Sembrerebbe che il sito risponda')
        return "OK"
    else:
        return "Telegram sent GET"



###################
# HANDLER PER RICHIESTE DALLA NODE-MCU
@istanza_server.route('/user', methods = ['GET', 'POST'])
def profile():
    if request.method == "GET":
        # Supponiamo di scrivere il seguente URL:
        # https://asd-care-server.herokuapp.com/user?ID=46810939&CONFIG=1

        # Recupero le informazioni URL-encoded
        codice_utente = request.args.get('ID')
        send_config = request.args.get('CONFIG')
        print("E' stata chiesta la presenza di {}".format(codice_utente))
        print("CONFIG {}".format(send_config))

        # Se l'utente e' riconosciuto, fornirgli il timestamp
        if (check_user(codice_utente)):
            # INFORMAZIONI DI DEBUG
            print(check_user(codice_utente))

            if int(send_config) == 1:
                # Cerco l'ultima chiave relativa all'utente caratterizzato da identificativo
                query_0 = db.session.query(ElencoUtenti.soglia_modulo, ElencoUtenti.soglia_durata)
                sub_query_1 = query_0.filter(ElencoUtenti.identificativo == str(codice_utente))
                sub_query_2 = sub_query_1.first()
                db.session.close()

                stringa = str()
                stringa += str(sub_query_2.soglia_modulo) + "," + str(sub_query_2.soglia_durata)
                print(stringa)

                #stringa_di_config = str(sub_query_2)
                return stringa

            else :
                #bot.send_message(chat_id=codice_utente, text="EMERGENZA: Crisi in atto! [GET]")

                #Recupero informazioni sul timestamp
                GMT_time = recupero_tempo_GMT()
                print(GMT_time)
                #GMT_TIME e' quello che passeremo a PostgreSQL. Non come sttringa

                #Invio del timestamp dalla Node-MCU
                return str(GMT_time)
        else:
            # INFORMAZIONI DI DEBUG
            print(check_user(codice_utente))
            return "Accesso negato. Assicurati di aver prima avviato il bot Telegram.\n", 520

    if request.method == "POST":
        # Supponiamo di scrivere il seguente URL:
        # https://asd-care-server.herokuapp.com/user?ID=46810939

        # Recupero le informazioni ottenute in formato JSON
        contenuto_ricevuto = request.get_json()
        # Estrapoliamo le informazioni dal JSON
        codice_utente = contenuto_ricevuto['user_ID'] #Mse volessi salvare il dato user_ID dentro cocide_utente E contemporaneamente toglierlo dall'oggeto che trasporto, uso pop
        timestamp_ricevuto = contenuto_ricevuto['Timestamp']
        accelerazione_ricevuta = contenuto_ricevuto['Acceleration']
        asse_x_ricevuto = contenuto_ricevuto['Ax']
        asse_y_ricevuto = contenuto_ricevuto['Ay']
        asse_z_ricevuto = contenuto_ricevuto['Az']
        allarme_ricevuto = contenuto_ricevuto['Alarm']

        print("INFO POST:\n {}\n {}\n {}\n {}\n {}\n {}\n {}\n".format(codice_utente,timestamp_ricevuto,accelerazione_ricevuta,asse_x_ricevuto,asse_y_ricevuto,asse_z_ricevuto,allarme_ricevuto))

        # Messaggio di servizio
        print("E stato chiesto di loggare un'occorrenza!\n")
        #print("chat_id : {}, Timestamp : {}\n ".format(codice_utente, timestamp_ricevuto))

        if (check_user(codice_utente)):
            for itemA, itemB, itemC ,itemD, itemE, itemF in list(zip(timestamp_ricevuto, accelerazione_ricevuta, asse_x_ricevuto, asse_y_ricevuto, asse_z_ricevuto, allarme_ricevuto)): #Scorre in parallelo le varie liste. Zip è necessario per prendere le tuple di tre elementi
                nuovo_dato = LogOccorrenze(identificativo=codice_utente, etichetta_tempo=itemA, accelerazione=itemB, asse_x=itemC, asse_y=itemD, asse_z=itemE, allarme=itemF)
                db.session.add(nuovo_dato)
            db.session.commit()
            db.session.close()


            if str(2) in allarme_ricevuto:
                idx = allarme_ricevuto.index("2")
                #Avviso l'utente
                bot.send_message(chat_id=codice_utente, text="EMERGENZA: Crisi in atto! [POST]\nOre: {}".format(timestamp_ricevuto[idx]))
            else :
                pass

        else :
            return "POST non andata a buon fine!\n", 530

        return "L'utente ha postato correttamente\n"



###################
# HANDLER PER URL ERRATI
@istanza_server.route('/<path:path>')
def catch_all(path):
    return 'Error, try just /'







###################
# Esecuzione dell'applicazione WSGI
if __name__ == '__main__':
    istanza_server.run()
