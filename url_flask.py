from flask import Flask, render_template, request, redirect, url_for, session  # Importing necessary modules from Flask
import requests  # Importing the requests module to make HTTP requests
from bs4 import BeautifulSoup  # Importing BeautifulSoup for web scraping
from nltk.tokenize import sent_tokenize, word_tokenize  # Importing NLTK for text tokenization
from nltk import pos_tag  # Importing NLTK for part-of-speech tagging
import psycopg2  # Importing psycopg2 for PostgreSQL database interaction
import nltk  # Importing NLTK
import os  # Importing the os module for environment variables

nltk.download('averaged_perceptron_tagger')  # Downloading NLTK data for part-of-speech tagging
nltk.download('punkt')  # Downloading NLTK data for tokenization
nltk.download('universal_tagset')  # Downloading NLTK data for universal tagset

app = Flask(__name__, template_folder='templates')  # Creating a Flask application instance
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key_here')  # Setting a secret key for session management

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', "admin@728")  # Setting the admin password from environment variables

# Connect to PostgreSQL database
conn = psycopg2.connect(
    dbname='news_database',  # Database name
    user='news_database_user',  # Database user
    password='Ix6xhxuSTz6qGh936wnPMKJwA4CeLs52',  # Database password
    host='dpg-cnmogjq1hbls739hkmtg-a'  # Database host
)
cur = conn.cursor()  # Creating a cursor object to execute PostgreSQL queries

# Creating a table if it doesn't exist to store news data
cur.execute('''CREATE TABLE IF NOT EXISTS url_news(
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
conn.commit()  # Committing the transaction to the database

# Function to clean text from HTML content
def clean_text(url):
    try:
        response = requests.get(url)  # Getting the webpage content
        soup = BeautifulSoup(response.text, 'html.parser')  # Parsing the HTML content
        paragraphs = soup.find_all('p')  # Finding all paragraphs
        news_text = ' '.join([p.get_text() for p in paragraphs])  # Concatenating text from paragraphs
        return news_text.strip() if news_text else "No news text found"  # Returning cleaned text or a message if no text found
    except Exception as e:
        return str(e)  # Returning error message if any exception occurs

# Function to analyze text including tokenization and part-of-speech tagging
def analyze_text(text):
    words = word_tokenize(text)  # Tokenizing text into words
    num_words = len(words)  # Counting the number of words
    sentences = sent_tokenize(text)  # Tokenizing text into sentences
    num_sentences = len(sentences)  # Counting the number of sentences
    pos_tags = pos_tag(words)  # Performing part-of-speech tagging
    noun_count, verb_count, adjective_count, adverb_count = count_pos_tags(pos_tags)  # Counting different parts of speech
    return num_words, num_sentences, noun_count, verb_count, adjective_count, adverb_count  # Returning analysis results

# Function to count different parts of speech
def count_pos_tags(pos_tags):
    noun_count = 0  # Initializing noun count
    verb_count = 0  # Initializing verb count
    adjective_count = 0  # Initializing adjective count
    adverb_count = 0  # Initializing adverb count

    for _, tag in pos_tags:  # Looping through each word and its corresponding part-of-speech tag
        if tag.startswith('NN'):  # Checking if the tag represents a noun
            noun_count += 1  # Incrementing noun count
        elif tag.startswith('VB'):  # Checking if the tag represents a verb
            verb_count += 1  # Incrementing verb count
        elif tag.startswith('JJ'):  # Checking if the tag represents an adjective
            adjective_count += 1  # Incrementing adjective count
        elif tag.startswith('RB'):  # Checking if the tag represents an adverb
            adverb_count += 1  # Incrementing adverb count

    return noun_count, verb_count, adjective_count, adverb_count  # Returning counts of different parts of speech

# Function to extract news heading from a webpage
def extract_news_heading(url):
    try:
        response = requests.get(url)  # Getting the webpage content
        soup = BeautifulSoup(response.text, 'html.parser')  # Parsing the HTML content
        heading_element = soup.title  # Finding the title element
        return heading_element.get_text().strip() if heading_element else "Heading not found"  # Returning the text of the title element or a message if not found
    except Exception as e:
        return str(e)  # Returning error message if any exception occurs

# Function to extract publication datetime from a webpage
def extract_publication_datetime(url):
    try:
        response = requests.get(url)  # Getting the webpage content
        soup = BeautifulSoup(response.text, 'html.parser')  # Parsing the HTML content
        pub = soup.find('div', class_='bLzcf HTz_b')  # Finding the publication datetime element
        return pub.get_text().strip() if pub else "Publication datetime not found"  # Returning the text of the publication datetime element or a message if not found
    except Exception as e:
        return str(e)  # Returning error message if any exception occurs

# Function to extract articles table from a webpage
def extract_articles_table(url):
    try:
        response = requests.get(url)  # Getting the webpage content
        soup = BeautifulSoup(response.text, 'html.parser')  # Parsing the HTML content

        articles_dict = {}  # Initializing dictionary to store article titles and links

        title_elements = soup.find_all(class_='yCs_c')  # Finding all elements with specified class for article titles
        link_elements = soup.find_all(class_='Hn2z7 undefined')  # Finding all elements with specified class for article links

        for title, link in zip(title_elements, link_elements):  # Iterating through title and link elements
            title_text = title.get_text().strip()  # Getting text of title element
            link_url = link['href']  # Getting URL from link element
            articles_dict[title_text] = link_url  # Adding title and link to dictionary

        return articles_dict  # Returning dictionary containing article titles and links

    except Exception as e:
        return {}  # Returning an empty dictionary if any exception occurs

# Function to store analysis results in the database
def store_analysis(url, news_heading, news_text, num_sentences, num_words, noun_count, verb_count, adjective_count, adverb_count, publication_datetime, article_links):
    try:
        cur.execute("""
            INSERT INTO url_news (url, news_heading, news_text, num_sentences, num_words, noun_count, verb_count, adjective_count, adverb_count, publication_datetime, article_titles, article_links) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (url) DO NOTHING
        """, (url, news_heading, news_text, num_sentences, num_words, noun_count, verb_count, adjective_count, adverb_count, publication_datetime, str(article_links.keys()), str(article_links.values())))

        conn.commit()  # Committing the transaction to the database
    except Exception as e:
        conn.rollback()  # Rolling back the transaction if an error occurs
        error_message = "Error storing analysis: {}".format(e)  # Constructing error message
        return render_template('error.html', error_message=error_message)  # Rendering error template with the error message

@app.route('/')  # Defining route for home page
def index():
    return render_template('index.html', error_message=None)  # Rendering index template with no error message

@app.route('/analyze', methods=['POST'])  # Defining route for analysis
def analyze():
    url = request.form['url']  # Getting URL from form data
    if not url.strip():  # Checking if URL is empty
        error_message = "Please enter a URL"  # Constructing error message
        return render_template('index.html', error_message=error_message)  # Rendering index template with the error message

    news_heading = extract_news_heading(url)  # Extracting news heading
    news_text = clean_text(url)  # Cleaning text from URL
    num_words, num_sentences, noun_count, verb_count, adjective_count, adverb_count = analyze_text(news_text)  # Analyzing text
    publication_datetime = extract_publication_datetime(url)  # Extracting publication datetime
    articles = extract_articles_table(url)  # Extracting articles table
    article_titles = list(articles.keys())  # Extracting article titles
    article_links = list(articles.values())  # Extracting article links

    store_analysis(url, news_heading, news_text, num_sentences, num_words, noun_count, verb_count, adjective_count, adverb_count, publication_datetime, articles)  # Storing analysis results

    return render_template('result.html',  # Rendering result template with analysis results
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

@app.route('/admin_panel')  # Defining route for admin panel
def admin_panel():
    if 'logged_in' not in session or not session['logged_in']:  # Checking if user is logged in
        return redirect(url_for('admin_login'))  # Redirecting to admin login page if not logged in

    cur.execute("SELECT url, news_heading, publication_datetime, num_sentences, num_words, noun_count, verb_count, adjective_count, adverb_count FROM url_news")  # Executing SQL query to fetch URL history
    url_history = cur.fetchall()  # Fetching URL history from database
    return render_template('history.html', url_history=url_history)  # Rendering history template with URL history data

@app.route('/admin_login', methods=['GET', 'POST'])  # Defining route for admin login
def admin_login():
    if request.method == 'POST':  # Checking if request method is POST
        entered_password = request.form['password']  # Getting entered password from form data
        if entered_password == ADMIN_PASSWORD:  # Checking if entered password is correct
            session['logged_in'] = True  # Setting session variable to indicate user is logged in
            return redirect(url_for('admin_panel'))  # Redirecting to admin panel if password is correct
        else:
            error_message = "Invalid password. Please try again."  # Constructing error message
            return render_template('login.html', error_message=error_message)  # Rendering login template with the error message if password is incorrect
    else:
        return render_template('login.html', error_message=None)  # Rendering login template with no error message for GET request

if __name__ == '__main__':  # Checking if the script is executed directly
    app.run(debug=True)  # Running the Flask application in debug mode

    
