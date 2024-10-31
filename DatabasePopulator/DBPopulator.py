from bs4 import BeautifulSoup  # Import BeautifulSoup for parsing HTML
import requests  # Import requests for making HTTP requests
from transformers import RobertaTokenizer, RobertaModel, RobertaForSequenceClassification
import torch
from sentence_transformers import SentenceTransformer
from playwright.sync_api import sync_playwright
import sqlite3
import os
import pickle


seasonCode = "WI24"  # Set the season code
os.environ["TOKENIZERS_PARALLELISM"] = "false"

model = SentenceTransformer("Alibaba-NLP/gte-Qwen2-1.5B-instruct",
                            trust_remote_code=True)
model.max_seq_length = 8192


# Request the main page for the specified season code and parse the HTML
mainPage = requests.get("https://classes.cornell.edu/browse/roster/" + seasonCode)
soup = BeautifulSoup(mainPage.text, "html.parser")



# Extract subject codes and names from the main page
subjectCodeTags = soup.findAll("li", attrs={"class":"browse-subjectcode"})
subjectNameSet = soup.findAll('li', attrs={"class":"browse-subjectdescr"})



# Initialize dictionaries for subject codes and names
subjectCodeLines = {}
subjectNames = {}
iterator = 0  # Iterator for tracking subject names



# Populate subjectCodeLines and subjectNames dictionaries
for line in subjectCodeTags:
    subjectTag = line.find("a")
    subjectName = subjectNameSet[iterator].find("a")
    if subjectTag:
        # Create URL for each subject and map to its name
        subjectCodeLines[subjectTag.text] = ("https://classes.cornell.edu/browse/roster/" + seasonCode + "/subject/" + subjectTag.text)
        subjectNames[subjectTag.text] = subjectName.text
    iterator += 1  # Increment the iterator for the next subject name



# Organize courses by subject codes into a dictionary
courses = {}
for subjectCode in subjectCodeLines.keys():
    tempCourses = []  # Temporary list for storing course codes
    subPage = requests.get(subjectCodeLines[subjectCode])  # Get the subject's webpage
    soup = BeautifulSoup(subPage.text, "html.parser")
    tempCourseNumbers = soup.findAll("div", attrs={"class":"title-subjectcode"})  # Extract course codes

    # Add course codes to the temporary list
    for classCode in tempCourseNumbers:
        name = str(classCode.getText())
        tempCourses.append(name)
    courses[subjectCode] = tempCourses  # Map subject code to its list of courses







# Create a roster of courses with descriptions
courseRoster = {}
courseCreditHours = {}
courseDistributions = {}
courseVectors = {}
courseRatings = {}
for subjectCode in courses.keys():
    subjectRoster = {}  # Dictionary for storing course descriptions per subject
    subjectCredits = {} # Dictionary for storing course credits per subject
    subjectDistributions = {} # Dictionary for storing course distributions per subject
    subjectVectors = {} # Dictionary for storing course description vectors
    subjectRatings = {} # Dictionary for storing course ratings
    for course in courses[subjectCode]:
        # Construct the URL for the specific course's details page
        websiteDomain = (subjectCodeLines[subjectCode][0:47] + "class/" + subjectCode + "/" +
                         course[len(course) - 4 : len(course)])
        coursePage = requests.get(websiteDomain)  # Get the course details page
        soup = BeautifulSoup(coursePage.text, "html.parser")

        # Extract course name using a specific ID pattern
        courseName = soup.find("a", id="dtitle-" + course.replace(" ", ""))
        if courseName:
            courseName = courseName.text.strip()  # Clean the course title

        # Extract the course description
        courseDescription = soup.find('p', class_='catalog-descr')
        if courseDescription:
            courseDescription = courseDescription.text.strip()  # Clean the description

        # Extract the amount of credit hourse
        creditHours = soup.find('span', class_='credit-val')
        if creditHours:
            creditHours = creditHours.text.strip() # Clean the number of credit hours

        # Extract the distribution categories
        courseDistribution = soup.find('span', class_='catalog-distr')
        if courseDistribution:
            courseDistribution = courseDistribution.text.strip()[22:len(courseDistribution.text)] # Clean the distributions string
        else:
            courseDistribution = ""


        overallRating = [-1.0, -1.0, -1.0]
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)

                # Open a new page
                page = browser.new_page()

                # Navigate to the website
                page.goto("https://www.cureviews.org/course/" + subjectCode + "/" +
                          course[len(course) - 4 : len(course)])
                # Wait for the rating element to load (adjust selector based on actual HTML)
                page.wait_for_selector("._rating_zvrrc_22", timeout=1000)
                # Extract the rating
                overallRating = page.query_selector_all("._rating_zvrrc_22")

                for i in range(3):
                    overallRating[i] = float(overallRating[i].text_content().strip())
            except Exception as e:
                overallRating = [-1.0, -1.0, -1.0]
            finally:
                # Close the browser
                browser.close()


        #Vector creation
        vector = model.encode(course + " | " + courseName + ": " + courseDescription,
                              convert_to_numpy = True)

        # Map course title to its description
        subjectRoster[course + " | " + courseName] = courseDescription
        subjectCredits[course + " | " + courseName] = creditHours
        subjectDistributions[course + " | " + courseName] = courseDistribution[0:
                                                                            len(courseDistribution)]
        subjectVectors[course + " | " + courseName] = vector
        subjectRatings[course + " | " + courseName] = overallRating
        print(course + " | " + courseName)

    courseRoster[subjectCode] = subjectRoster  # Store the subject roster descriptions
    courseCreditHours[subjectCode] = subjectCredits # Store the subject credits
    courseDistributions[subjectCode] = subjectDistributions # Store the subject distributions
    courseVectors[subjectCode] = subjectVectors # Store the subject vectors
    courseRatings[subjectCode] = subjectRatings # Store the subject ratings




# Connect to SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect(seasonCode + ".db")  # Specify your database name

# Create a cursor object
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL,
    subject TEXT NOT NULL,
    course_number INTEGER NOT NULL,
    description TEXT,
    description_vector BLOB,
    distributions TEXT,
    credits TEXT,
    is_fws BOOLEAN NOT NULL,
    is_lad BOOLEAN NOT NULL
)
''')
conn.commit()

count = 0
for key in courseRoster.keys():
    for sub_key in courseRoster[key].keys():
        print(sub_key)
        id = count
        full_name = sub_key
        subject = key
        courseNumber = sub_key[len(sub_key) - 4 : len(sub_key)]
        description = courseRoster[key][sub_key]
        #TODO fix
        vector_blob = pickle.dumps(courseVectors[key][sub_key])
        distributions = courseDistributions[key][sub_key]
        credits = courseCreditHours[key][sub_key]
        fws = ("FWS" in sub_key)
        lad = ("CA" in distributions or "LA" in distributions or "LAD" in distributions
               or "ALC" in distributions or "SCD" in distributions or "HA" in distributions
               or "HST" in distributions or "KCM" in distributions or "ETM" in distributions
               or "SBA" in distributions or "SSC" in distributions or "GLC" in distributions
               or "FL" in distributions or "CE" in distributions)
        count += 1

        cursor.execute('''
            INSERT INTO courses (id, full_name, subject, course_number, description, 
            description_vector, distributions, credits, is_fws, is_lad) VALUES 
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (id, full_name, subject,
            courseNumber, description, vector_blob, distributions, credits, fws, lad))
        conn.commit()
conn.close()
