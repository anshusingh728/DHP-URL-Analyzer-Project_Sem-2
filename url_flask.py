from flask import Flask, render_template, request, redirect, url_for, session
import requests
from bs4 import BeautifulSoup
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk import pos_tag
import psycopg2
import nltk
nltk.download('punkt')
nltk.download('universal_tagset')
app = Flask(__name__, template_folder='templates')
app.secret_key = 'your_secret_key_here'  # Set the secret key used by Flask to securely sign session.

# Connect to PostgreSQL database
conn = psycopg2.connect(dbname='news_database', user='news_database_user', password='Ix6xhxuSTz6qGh936wnPMKJwA4CeLs52', host='dpg-cnmogjq1hbls739hkmtg-a')
cur = conn.cursor()

ADMIN_PASSWORD = "admin@728"  # Password required to access the admin panel.

# Create or check if the table exists in the PostgreSQL database
cur.execute('''CREATE TABLE IF NOT EXISTS url_data(
            url TEXT PRIMARY KEY,
            news_heading TEXT,
            news_text TEXT,
            num_sentences INTEGER,
            num_words INTEGER,
            pos_tags TEXT,
            count_postags INTEGER,
            publication_datetime TEXT,
            article_titles TEXT,
            article_links TEXT
        )''')
conn.commit()

# Extract and clean news text
def clean_text(url):
    try:
        response = requests.get(url) #it sends an HTTP GET request to the specified url using the requests.get() 
        soup = BeautifulSoup(response.text, 'html.parser')#it creates a object soup by parsing the HTML content 
        #of the webpage obtained from the response. It uses the 'html.parser' parser to parse the HTML.
        paragraphs = soup.find_all('p')#This line finds all <p> (paragraph) elements within the parsed HTML document
        news_text = ' '.join([p.get_text() for p in paragraphs])#extracts the text content of each paragraph
        #t uses list comprehension to iterate over each paragraph (p) in the paragraphs list
        # and extract its text using the get_text()
        return news_text.strip() if news_text else "No news text found" # return the cleaned news text if found
    except Exception as e:
        return str(e)

# Function to analyze text
def analyze_text(text):
    words = word_tokenize(text)#It tokenizes the input text into individual words
    num_words = len(words)#number of words in the tokenized text
    sentences = sent_tokenize(text)# tokenizes the input text into individual sentences 
    num_sentences = len(sentences) #number of sentences in the tokenized text
    pos_tags = pos_tag(words, tagset="universal")# it performs part-of-speech (POS) tagging on the list of words using the pos_tag()
        #tagset="universal" argument specifies the tagset to be used, which is the Universal POS tagset.
    count_postags=len(pos_tags) #number of postags
    return num_words, num_sentences, pos_tags,count_postags

# Function to extract news heading from URL
def extract_news_heading(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        heading_element = soup.title#This line selects the <title> element from the parsed HTML document using the title attribute 
        # title contain news heading
        return heading_element.get_text().strip() if heading_element else "Heading not found"#If a title tag exists, this line extracts the text content of the title tag using the get_text()
            #It also removes any leading or trailing whitespace from the extracted text using the strip() method.
    except Exception as e:
        return str(e)

# Function to extract publication datetime from URL
#The publication datetime is extracted only from the <div> element with the class 'bLzcf HTz_b' 
# within the parsed HTML content.
def extract_publication_datetime(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        pub = soup.find('div', class_='bLzcf HTz_b')
        return pub.get_text().strip() if pub else "Publication datetime not found"#it retrieves the text content of the current element (pub) 
            # Check if the extracted datetime looks like a valid publication datetime
    except Exception as e:
        return str(e)

# Function to extract articles table from URL
def extract_articles_table(url):
    try:
        response = requests.get(url)        # Send a GET request to the provided URL

        soup = BeautifulSoup(response.text, 'html.parser')        # Parse the HTML content of the response using BeautifulSoup

        articles_dict = {}        # Initialize an empty dictionary to store article titles and their corresponding links

        title_elements = soup.find_all(class_='yCs_c')        # Find all elements with class 'yCs_c' which typically represent article titles

        link_elements = soup.find_all(class_='Hn2z7 undefined')        # Find all elements with class 'Hn2z7 undefined' which typically represent article links

        for title, link in zip(title_elements, link_elements):        # Iterate over the title and link elements using zip

            title_text = title.get_text().strip()            # Extract text from the title element and remove leading/trailing whitespaces

            link_url = link['href']            # Extract the 'href' attribute from the link element to get the URL

            articles_dict[title_text] = link_url             # Add the title and link URL to the articles_dict

        return articles_dict         # Return the dictionary containing article titles and links

    except Exception as e:
                # If an error occurs during the process, return an empty dictionary

        return {}

# Function to store analysis data in the database
def store_analysis(url, news_heading, news_text, num_sentences, num_words, pos_tags, publication_datetime,count_postags,article_links):
    try:
        cur.execute("""
        INSERT INTO url_data (url, news_heading, news_text, num_sentences, num_words, pos_tags, publication_datetime, count_postags, article_links) 
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (url) DO NOTHING
        """, (url, news_heading, news_text, num_sentences, num_words, str(pos_tags), publication_datetime,count_postags, article_links))
        #inserts data into the url_textdb table with the specified columns 
    #The %s placeholders in the statement are replaced with the values provided in the tuple
    # ON CONFLICT (url) DO NOTHING this is doing : if duplicate submissition of urls the insertion will skipped.
        conn.commit() #It saves the changes made by the INSERT statement permanently.
    except Exception as e:
        conn.rollback()
        print("Error storing analysis:", e)

@app.route('/')
def index():
    return render_template('index.html', error_message=None)

@app.route('/analyze', methods=['POST'])
def analyze():
    # Retrieve the URL from the form data
    url = request.form['url']
    # Check if the URL is empty or consists only of whitespace
    if not url.strip():
        # If URL is empty, set error_message and render index.html template again
        error_message = "Please enter a URL"
        return render_template('index.html', error_message=error_message)
# Extract news heading, clean text, analyze text, extract publication datetime, and extract articles
    news_heading = extract_news_heading(url)     # Extract news heading from the provided URL

    news_text = clean_text(url)     # Clean the text extracted from the URL (remove HTML tags, etc.)
    # Analyze the cleaned text to get the number of words, sentences, and POS tags
    num_words, num_sentences, pos_tags,count_postags = analyze_text(news_text)
    publication_datetime = extract_publication_datetime(url)    # Extract publication datetime from the provided URL
    articles = extract_articles_table(url)    # Extract articles table from the provided URL
    article_titles = list(articles.keys())    # Get the titles of the articles extracted
    article_links = list(articles.values())    # Get the links of the articles extracted

    # Store the analysis in the database
    store_analysis(url, news_heading, news_text, num_sentences, num_words, pos_tags, publication_datetime,count_postags, article_links)
     # Render the result.html template with analysis data
    return render_template('result.html', 
                           url=url, 
                           news_heading=news_heading, 
                           news_text=news_text, 
                           num_sentences=num_sentences, 
                           num_words=num_words, 
                           pos_tags=pos_tags, 
                           publication_datetime=publication_datetime, 
                           articles=articles, 
                           article_titles=article_titles, 
                           article_links=article_links, 
                           zip=zip)

@app.route('/admin_panel') # Define route for the admin panel

def admin_panel():
    # Check if the user is logged in, if not, redirect to admin login page
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('admin_login'))
    
    # Fetch URL history from the database and render history.html template
    cur.execute("SELECT url, news_heading, publication_datetime, num_sentences, num_words,count_postags FROM url_data")
    url_history = cur.fetchall()
    return render_template('history.html', url_history=url_history)

# Define route for admin login page (GET and POST requests)
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
     # Check if the form is submitted
    if request.method == 'POST':
        # Retrieve the entered password from the form data
        entered_password = request.form['password']
        # Check if the entered password matches the predefined admin password
        if entered_password == ADMIN_PASSWORD:
        # If password is correct, set session variable and redirect to admin panel
            session['logged_in'] = True
            return redirect(url_for('admin_panel'))
        else:
            # If password is incorrect, set error_message and render login.html template again

            error_message = "Invalid password. Please try again."
            return render_template('login.html', error_message=error_message)
    else:
        # Render the login.html template without error_message
        return render_template('login.html', error_message=None)
    
# Run the app in debug mode
if __name__ == '__main__':
            app.run(debug=True)


