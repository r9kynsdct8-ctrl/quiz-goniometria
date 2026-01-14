from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.window import Window
import random
import json
import os
import requests
from datetime import datetime

# ============================================
# CONFIGURAZIONE FIREBASE
# ============================================
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyBjXKVLWapuDME9Ifm83YFRDJsSxV-kNqE",
    "authDomain": "analisi67-2fbe0.firebaseapp.com",
    "projectId": "analisi67-2fbe0",
    "databaseURL": "https://analisi67-2fbe0-default-rtdb.firebaseio.com"
}

FIRESTORE_URL = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_CONFIG['projectId']}/databases/(default)/documents"

# ============================================
# QUI INSERISCI LE TUE DOMANDE E RISPOSTE
# ============================================
DOMANDE = [
    {
        "formula": "sin²(x) + cos²(x) = ?",
        "opzioni": ["1", "0", "2", "sin(x)"],
        "corretta": 0
    },
    {
        "formula": "tan(x) = ?",
        "opzioni": ["sin(x)/cos(x)", "cos(x)/sin(x)", "sin(x)·cos(x)", "1/sin(x)"],
        "corretta": 0
    },
    {
        "formula": "sin(2x) = ?",
        "opzioni": ["2sin(x)", "2sin(x)cos(x)", "sin²(x)", "2cos(x)"],
        "corretta": 1
    },
    # AGGIUNGI QUI ALTRE DOMANDE
]

class FirebaseHelper:
    @staticmethod
    def salva_punteggio(nome, punteggio):
        try:
            data = {
                "fields": {
                    "nome": {"stringValue": nome},
                    "punteggio": {"integerValue": str(punteggio)},
                    "data": {"stringValue": datetime.now().strftime('%d/%m/%Y %H:%M')},
                    "timestamp": {"integerValue": str(int(datetime.now().timestamp()))}
                }
            }
            response = requests.post(
                f"{FIRESTORE_URL}/classifica?key={FIREBASE_CONFIG['apiKey']}",
                json=data,
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Errore salvataggio: {e}")
            return False
    
    @staticmethod
    def carica_classifica():
        try:
            response = requests.get(
                f"{FIRESTORE_URL}/classifica?key={FIREBASE_CONFIG['apiKey']}",
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                classifica = []
                
                if 'documents' in data:
                    for doc in data['documents']:
                        fields = doc['fields']
                        classifica.append({
                            'nome': fields['nome']['stringValue'],
                            'punteggio': int(fields['punteggio']['integerValue']),
                            'data': fields['data']['stringValue']
                        })
                    
                    classifica.sort(key=lambda x: x['punteggio'], reverse=True)
                return classifica
            return []
        except Exception as e:
            print(f"Errore caricamento: {e}")
            return []

class NomeUtenteScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        title = Label(text='Benvenuto!\nInserisci il tuo nome', 
                     font_size='28sp', 
                     size_hint=(1, 0.3),
                     halign='center')
        
        self.input_nome = TextInput(hint_text='Il tuo nome',
                                   font_size='24sp',
                                   size_hint=(1, 0.15),
                                   multiline=False)
        
        btn_conferma = Button(text='Inizia', 
                            font_size='24sp',
                            size_hint=(1, 0.15),
                            background_color=(0.2, 0.6, 1, 1))
        btn_conferma.bind(on_press=self.salva_nome)
        
        layout.add_widget(title)
        layout.add_widget(Label(size_hint=(1, 0.2)))
        layout.add_widget(self.input_nome)
        layout.add_widget(btn_conferma)
        layout.add_widget(Label(size_hint=(1, 0.2)))
        self.add_widget(layout)
    
    def salva_nome(self, instance):
        nome = self.input_nome.text.strip()
        if nome:
            with open('utente.json', 'w') as f:
                json.dump({'nome': nome}, f)
            self.manager.current = 'menu'

class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        title = Label(text='Quiz Formule\nGoniometriche', 
                     font_size='32sp', 
                     size_hint=(1, 0.4),
                     halign='center')
        
        btn_gioca = Button(text='Inizia Quiz', 
                          font_size='24sp',
                          size_hint=(1, 0.2),
                          background_color=(0.2, 0.6, 1, 1))
        btn_gioca.bind(on_press=self.start_quiz)
        
        btn_classifica = Button(text='Classifica', 
                               font_size='24sp',
                               size_hint=(1, 0.2),
                               background_color=(0.3, 0.7, 0.3, 1))
        btn_classifica.bind(on_press=self.show_classifica)
        
        layout.add_widget(title)
        layout.add_widget(btn_gioca)
        layout.add_widget(btn_classifica)
        self.add_widget(layout)
    
    def start_quiz(self, instance):
        self.manager.get_screen('quiz').reset_quiz()
        self.manager.current = 'quiz'
    
    def show_classifica(self, instance):
        self.manager.current = 'classifica'

class QuizScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.punteggio = 0
        self.tempo_rimasto = 120
        self.domande_shuffle = []
        self.indice_corrente = 0
        
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        top_layout = BoxLayout(size_hint=(1, 0.1), spacing=10)
        self.label_timer = Label(text='Tempo: 2:00', font_size='20sp')
        self.label_punteggio = Label(text='Punteggio: 0', font_size='20sp')
        top_layout.add_widget(self.label_timer)
        top_layout.add_widget(self.label_punteggio)
        
        self.label_domanda = Label(text='', 
                                   font_size='24sp',
                                   size_hint=(1, 0.3),
                                   halign='center',
                                   valign='middle')
        self.label_domanda.bind(size=self.label_domanda.setter('text_size'))
        
        self.bottoni_risposte = []
        for i in range(4):
            btn = Button(text='', 
                        font_size='18sp',
                        size_hint=(1, 0.15))
            btn.bind(on_press=lambda x, idx=i: self.check_risposta(idx))
            self.bottoni_risposte.append(btn)
        
        self.layout.add_widget(top_layout)
        self.layout.add_widget(self.label_domanda)
        for btn in self.bottoni_risposte:
            self.layout.add_widget(btn)
        
        self.add_widget(self.layout)
        self.timer_event = None
    
    def reset_quiz(self):
        self.punteggio = 0
        self.tempo_rimasto = 120
        self.indice_corrente = 0
        self.domande_shuffle = DOMANDE.copy()
        random.shuffle(self.domande_shuffle)
        self.label_punteggio.text = 'Punteggio: 0'
        self.mostra_domanda()
        if self.timer_event:
            self.timer_event.cancel()
        self.timer_event = Clock.schedule_interval(self.update_timer, 1)
    
    def mostra_domanda(self):
        if self.indice_corrente >= len(self.domande_shuffle):
            self.indice_corrente = 0
            random.shuffle(self.domande_shuffle)
        
        domanda = self.domande_shuffle[self.indice_corrente]
        self.label_domanda.text = domanda['formula']
        
        opzioni_shuffle = list(enumerate(domanda['opzioni']))
        random.shuffle(opzioni_shuffle)
        
        self.mapping_risposte = {}
        for i, (idx_originale, testo) in enumerate(opzioni_shuffle):
            self.bottoni_risposte[i].text = testo
            self.bottoni_risposte[i].background_color = (0.3, 0.3, 0.3, 1)
            self.mapping_risposte[i] = idx_originale
    
    def check_risposta(self, idx_bottone):
        domanda = self.domande_shuffle[self.indice_corrente]
        idx_risposta = self.mapping_risposte[idx_bottone]
        
        if idx_risposta == domanda['corretta']:
            self.punteggio += 1
            self.bottoni_risposte[idx_bottone].background_color = (0.2, 0.8, 0.2, 1)
        else:
            self.bottoni_risposte[idx_bottone].background_color = (0.8, 0.2, 0.2, 1)
        
        self.label_punteggio.text = f'Punteggio: {self.punteggio}'
        Clock.schedule_once(lambda dt: self.prossima_domanda(), 0.5)
    
    def prossima_domanda(self):
        self.indice_corrente += 1
        self.mostra_domanda()
    
    def update_timer(self, dt):
        self.tempo_rimasto -= 1
        minuti = self.tempo_rimasto // 60
        secondi = self.tempo_rimasto % 60
        self.label_timer.text = f'Tempo: {minuti}:{secondi:02d}'
        
        if self.tempo_rimasto <= 0:
            self.timer_event.cancel()
            self.fine_quiz()
    
    def fine_quiz(self):
        self.salva_punteggio()
        result_screen = self.manager.get_screen('risultato')
        result_screen.mostra_risultato(self.punteggio)
        self.manager.current = 'risultato'
    
    def salva_punteggio(self):
        nome_utente = 'Anonimo'
        if os.path.exists('utente.json'):
            with open('utente.json', 'r') as f:
                dati = json.load(f)
                nome_utente = dati.get('nome', 'Anonimo')
        
        FirebaseHelper.salva_punteggio(nome_utente, self.punteggio)

class RisultatoScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        self.label_risultato = Label(text='', 
                                    font_size='32sp',
                                    size_hint=(1, 0.5))
        
        btn_menu = Button(text='Torna al Menu', 
                         font_size='24sp',
                         size_hint=(1, 0.2))
        btn_menu.bind(on_press=lambda x: setattr(self.manager, 'current', 'menu'))
        
        btn_riprova = Button(text='Riprova', 
                           font_size='24sp',
                           size_hint=(1, 0.2),
                           background_color=(0.2, 0.6, 1, 1))
        btn_riprova.bind(on_press=self.riprova)
        
        self.layout.add_widget(self.label_risultato)
        self.layout.add_widget(btn_riprova)
        self.layout.add_widget(btn_menu)
        self.add_widget(self.layout)
    
    def mostra_risultato(self, punteggio):
        self.label_risultato.text = f'Tempo scaduto!\n\nPunteggio finale:\n{punteggio}'
    
    def riprova(self, instance):
        self.manager.get_screen('quiz').reset_quiz()
        self.manager.current = 'quiz'

class ClassificaScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        title = Label(text='Classifica Globale', 
                     font_size='28sp',
                     size_hint=(1, 0.15))
        
        self.label_classifica = Label(text='Caricamento...',
                                     font_size='18sp',
                                     size_hint=(1, 0.7),
                                     halign='left',
                                     valign='top')
        self.label_classifica.bind(size=self.label_classifica.setter('text_size'))
        
        btn_indietro = Button(text='Indietro', 
                            font_size='20sp',
                            size_hint=(1, 0.15))
        btn_indietro.bind(on_press=lambda x: setattr(self.manager, 'current', 'menu'))
        
        self.layout.add_widget(title)
        self.layout.add_widget(self.label_classifica)
        self.layout.add_widget(btn_indietro)
        self.add_widget(self.layout)
    
    def on_enter(self):
        Clock.schedule_once(lambda dt: self.carica_classifica(), 0.1)
    
    def carica_classifica(self):
        self.label_classifica.text = 'Caricamento...'
        classifica = FirebaseHelper.carica_classifica()
        
        if not classifica:
            self.label_classifica.text = 'Nessun punteggio ancora o errore di connessione'
            return
        
        testo = ''
        for i, record in enumerate(classifica[:10], 1):
            nome = record.get('nome', 'Anonimo')
            testo += f"{i}. {nome} - {record['punteggio']} punti\n   {record['data']}\n\n"
        
        self.label_classifica.text = testo

class QuizApp(App):
    def build(self):
        Window.clearcolor = (0.1, 0.1, 0.1, 1)
        sm = ScreenManager()
        
        sm.add_widget(NomeUtenteScreen(name='nome_utente'))
        sm.add_widget(MenuScreen(name='menu'))
        sm.add_widget(QuizScreen(name='quiz'))
        sm.add_widget(RisultatoScreen(name='risultato'))
        sm.add_widget(ClassificaScreen(name='classifica'))
        
        if os.path.exists('utente.json'):
            sm.current = 'menu'
        else:
            sm.current = 'nome_utente'
        
        return sm

if __name__ == '__main__':
    QuizApp().run()