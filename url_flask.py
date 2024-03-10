from flask import Flask, render_template, request, redirect, url_for, session
import requests
from bs4 import BeautifulSoup
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk import pos_tag
import psycopg2
import nltk
nltk.download('averaged_perceptron_tagger')

nltk.download('punkt')
nltk.download('universal_tagset')
app = Flask(__name__, template_folder='templates')
app.secret_key = 'your_secret_key_here'  # Set the secret key used by Flask to securely sign session.

# Connect to PostgreSQL database
conn = psycopg2.connect(dbname='news_database', user='news_database_user', password='Ix6xhxuSTz6qGh936wnPMKJwA4CeLs52', host='dpg-cnmogjq1hbls739hkmtg-a')
cur = conn.cursor()

ADMIN_PASSWORD = "admin@728"  # Password required to access the admin panel.

cur.execute('''CREATE TABLE IF NOT EXISTS url_data(
            url TEXT PRIMARY KEY,
            news_heading TEXT,
            news_text TEXT,
            num_sentences INTEGER,
            num_words INTEGER,
            noun_count INTEGER,
            verb_count INTEGER,
            adjective_count INTEGER,
            adverb_count INTEGER,
            publication_datetime TEXT,
            article_titles TEXT,
            article_links TEXT
        )''')
conn.commit()

def clean_text(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        paragraphs = soup.find_all('p')
        news_text = ' '.join([p.get_text() for p in paragraphs])
        return news_text.strip() if news_text else "No news text found"
    except Exception as e:
        return str(e)

def analyze_text(text):
    words = word_tokenize(text)
    num_words = len(words)
    sentences = sent_tokenize(text)
    num_sentences = len(sentences)
    pos_tags = pos_tag(words)
    noun_count, verb_count, adjective_count, adverb_count = count_pos_tags(pos_tags)
    return num_words, num_sentences, noun_count, verb_count, adjective_count, adverb_count

def count_pos_tags(pos_tags):
    noun_count = 0
    verb_count = 0
    adjective_count = 0
    adverb_count = 0

    for _, tag in pos_tags:
        if tag.startswith('NN'):  # Noun
            noun_count += 1
        elif tag.startswith('VB'):  # Verb
            verb_count += 1
        elif tag.startswith('JJ'):  # Adjective
            adjective_count += 1
        elif tag.startswith('RB'):  # Adverb
            adverb_count += 1

    return noun_count, verb_count, adjective_count, adverb_count

def extract_news_heading(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        heading_element = soup.title
        return heading_element.get_text().strip() if heading_element else "Heading not found"
    except Exception as e:
        return str(e)

def extract_publication_datetime(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        pub = soup.find('div', class_='bLzcf HTz_b')
        return pub.get_text().strip() if pub else "Publication datetime not found"
    except Exception as e:
        return str(e)

def extract_articles_table(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        articles_dict = {}

        title_elements = soup.find_all(class_='yCs_c')
        link_elements = soup.find_all(class_='Hn2z7 undefined')

        for title, link in zip(title_elements, link_elements):
            title_text = title.get_text().strip()
            link_url = link['href']
            articles_dict[title_text] = link_url

        return articles_dict

    except Exception as e:
        return {}

def store_analysis(url, news_heading, news_text, num_sentences, num_words, noun_count, verb_count, adjective_count, adverb_count, publication_datetime, article_links):
    try:
        cur.execute("""
            INSERT INTO url_data (url, news_heading, news_text, num_sentences, num_words, noun_count, verb_count, adjective_count, adverb_count, publication_datetime, article_titles, article_links) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (url) DO NOTHING
        """, (url, news_heading, news_text, num_sentences, num_words, noun_count, verb_count, adjective_count, adverb_count, publication_datetime, str(article_links.keys()), str(article_links.values())))

        conn.commit()
    except Exception as e:
        conn.rollback()
        error_message = "Error storing analysis: {}".format(e)
        return render_template('error.html', error_message=error_message)

@app.route('/')
def index():
    return render_template('index.html', error_message=None)

@app.route('/analyze', methods=['POST'])
def analyze():
    url = request.form['url']
    if not url.strip():
        error_message = "Please enter a URL"
        return render_template('index.html', error_message=error_message)

    news_heading = extract_news_heading(url)
    news_text = clean_text(url)
    num_words, num_sentences, noun_count, verb_count, adjective_count, adverb_count = analyze_text(news_text)
    publication_datetime = extract_publication_datetime(url)
    articles = extract_articles_table(url)
    article_titles = list(articles.keys())
    article_links = list(articles.values())

    store_analysis(url, news_heading, news_text, num_sentences, num_words, noun_count, verb_count, adjective_count, adverb_count, publication_datetime, articles)

    return render_template('result.html', 
                           url=url, 
                           news_heading=news_heading, 
                           news_text=news_text, 
                           num_sentences=num_sentences, 
                           num_words=num_words, 
                           noun_count=noun_count, 
                           verb_count=verb_count, 
                           adjective_count=adjective_count, 
                           adverb_count=adverb_count, 
                           publication_datetime=publication_datetime, 
                           articles=articles, 
                           article_titles=article_titles, 
                           article_links=article_links, 
                           zip=zip)

@app.route('/admin_panel')
def admin_panel():
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('admin_login'))

    cur.execute("SELECT url, news_heading, publication_datetime, num_sentences, num_words, noun_count, verb_count, adjective_count, adverb_count FROM url_data")
    url_history = cur.fetchall()
    return render_template('history.html', url_history=url_history)

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        entered_password = request.form['password']
        if entered_password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin_panel'))
        else:
            error_message = "Invalid password. Please try again."
            return render_template('login.html', error_message=error_message)
    else:
        return render_template('login.html', error_message=None)

if __name__ == '__main__':
    app.run(debug=True)
