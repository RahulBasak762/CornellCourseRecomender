from bs4 import BeautifulSoup  # Import BeautifulSoup for parsing HTML
import requests  # Import requests for making HTTP requests
import os  # Import os for operating system interaction
from transformers import BertModel, BertTokenizer,RobertaTokenizer, RobertaModel
import torch

seasonCode = "SU24"  # Set the season code


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




# Load pre-trained RoBERTa tokenizer
tokenizer = RobertaTokenizer.from_pretrained('roberta-small')

# Load pre-trained RoBERTa model for sequence classification (e.g., binary classification)
model = RobertaModel.from_pretrained('roberta-small')




# Create a roster of courses with descriptions
courseRoster = {}
courseCreditHours = {}
courseDistributions = {}
courseVectors = {}
for subjectCode in courses.keys():
    subjectRoster = {}  # Dictionary for storing course descriptions per subject
    subjectCredits = {} # Dictionary for storing course credits per subject
    subjectDistributions = {} # Dictionary for storing course distributions per subject
    subjectVectors = {}
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
            courseDistribution = courseDistribution.text.strip() # Clean the distributions string
        else:
            courseDistribution = ""

        #Vector creation
        # Tokenize input text
        inputs = tokenizer(courseDescription, return_tensors='pt', max_length=256, truncation=True,
                           padding='max_length')

        with torch.no_grad():  # Disable gradients
            outputs = model(**inputs)

        # Get embeddings from the last hidden layer
        last_hidden_states = outputs.last_hidden_state

        # CLS token embedding
        embeddedCourseTokenCLS = last_hidden_states[:, 0, :]

        # Map course title to its description
        subjectRoster[course + " | " + courseName] = courseDescription
        subjectCredits[course + " | " + courseName] = creditHours
        subjectDistributions[course + " | " + courseName] = courseDistribution
        subjectVectors[course + " | " + courseName] = embeddedCourseTokenCLS

    courseRoster[subjectCode] = subjectRoster  # Store the subject roster
    courseCreditHours[subjectCode] = subjectCredits # Store the subject credits
    courseDistributions[subjectCode] = subjectDistributions # Store the subject distributions
    courseVectors[subjectCode] = subjectVectors





#TODO Database

# Write the collected course data to a text file
# file_name = "roster-" + seasonCode + ".txt"  # Define the output filename
# with open(file_name, 'w') as file:  # Open file for writing
#     for subjectCode in courseRoster.keys():
#         # Write subject code and name
#         file.write("\n\n$" + subjectCode + " | " + subjectNames[subjectCode] + "$\n")
#         for course in courseRoster[subjectCode].keys():
#             file.write("&" + course + "&\n")  # Write course title
#             file.write("#" + courseRoster[subjectCode][course] + "#\n")  # Write course description
#
# file.close()  # Close the file
