from bs4 import BeautifulSoup
import requests
from datetime import date

#Find current date
day = int(date.today().day)
month = int(str(date.today().month))
year = str(date.today().year)[2:4]
seasonCode = ""

#Semester Schedule
if (month == 8 and day >= 26) or (month >=9 and month <= 12) or (month == 1 and day == 1):
    seasonCode = "FA"
elif (month == 1 and day <= 20):
    seasonCode = "WI"
elif (month < 5) or (month == 5 and day <= 25):
    seasonCode = "SP"
else:
    seasonCode = "SU"
seasonCode += year

#TODO MANUEL SEARCH
seasonCode = "SU24"



mainPage = requests.get("https://classes.cornell.edu/browse/roster/" + seasonCode)
soup = BeautifulSoup(mainPage.text, "html.parser")
subjectCodeTags = soup.findAll("li", attrs={"class":"browse-subjectcode"})
subjectNameSet = soup.findAll('li', attrs={"class":"browse-subjectdescr"})



#Dictionary of subject websites, with subject code being the key
subjectCodeLines = {}
subjectNames = {}
iterator = 0
for line in subjectCodeTags:
    subjectTag = line.find("a")
    subjectName = subjectNameSet[iterator].find("a")
    if subjectTag:
        #populate subjectCodes and subjectSites
        subjectCodeLines[subjectTag.text] = ("https://classes.cornell.edu/browse/roster/" + seasonCode + "/subject/" + subjectTag.text)
        subjectNames[subjectTag.text] = subjectName.text
    iterator += 1




#Organize a dictionary, with subjectCodes being the key, and the definition being an array of all
#individual courseCodes Ex: courses["CS"] = [CS 1110, CS 1112, CS 2110...]
courses = {}
for subjectCode in subjectCodeLines.keys():
    tempCourses = []
    subPage = requests.get(subjectCodeLines[subjectCode])
    soup = BeautifulSoup(subPage.text, "html.parser")
    tempCourseNumbers = soup.findAll("div", attrs={"class":"title-subjectcode"})
    for classCode in tempCourseNumbers:
        name = str(classCode.getText())
        tempCourses.append(name)
    courses[subjectCode] = tempCourses



#Web scrape for descriptions of all courses. By subject, make a dictionary consisting of all courses
#and there description. After, replace courses[subject] with the dictionary including descriptions




courseRoster = {}
#Format, courseRoster["CS"] = {"CS 2110 | Data Structures and OOP": "Description", ..."
for subjectCode in courses.keys():
    subjectRoster = {}
    for course in courses[subjectCode]:
        websiteDomain = (subjectCodeLines[subjectCode][0:47] + "class/" + subjectCode + "/" +
                         course[len(course) - 4 : len(course)])
        coursePage = requests.get(websiteDomain)
        soup = BeautifulSoup(coursePage.text, "html.parser")
        courseName = soup.find("a", id="dtitle-" + course.replace(" ", ""))
        if courseName:
            courseName = courseName.text.strip()
        courseDescription = soup.find('p', class_='catalog-descr')
        if courseDescription:
            courseDescription = courseDescription.text.strip()
        subjectRoster[course + " | " + courseName] = courseDescription
    courseRoster[subjectCode] = subjectRoster



#write to file
file_name = "roster-" + seasonCode + ".txt"
with open(file_name, 'w') as file:
    for subjectCode in courseRoster.keys():
        file.write("\n\n$" + subjectCode + " | " + subjectNames[subjectCode] + "$\n")
        for course in courseRoster[subjectCode].keys():
            file.write("&" + course + "&\n")
            file.write("#" + courseRoster[subjectCode][course] + "#\n")

file.close()











