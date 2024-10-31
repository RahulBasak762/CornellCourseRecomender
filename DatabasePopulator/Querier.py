import sqlite3
from sentence_transformers import SentenceTransformer
import pickle

model = SentenceTransformer("Alibaba-NLP/gte-Qwen2-1.5B-instruct",
                            trust_remote_code=True)
model.max_seq_length = 8192

def query(seasonCode, description, fws, lad):
    # Connect to SQLite database (or create it if it doesn't exist)
    conn = sqlite3.connect(seasonCode + ".db")  # Specify your database name

    # Create a cursor object
    cursor = conn.cursor()

    userInput = description
    vector = model.encode(userInput, convert_to_numpy = True)


    query = "SELECT description_vector, full_name FROM courses"

    if (fws):
        query += " WHERE is_fws = 1"
    if (lad):
        query += " WHERE is_lad = 1"

    cursor.execute(query)
    courseList = cursor.fetchall()
    ratedCourses = []
    for item in courseList:
        name = item[1]
        item = pickle.loads(item[0])
        similarityScore = model.similarity(vector, item).item()
        ratedCourses.append([name, similarityScore])

    ratedCourses = sorted(ratedCourses, key=lambda x: x[1])
    ratedCourses.reverse()

    print("Classes most similar to: " + userInput)

    for i in range(30):
        print(ratedCourses[i][0] + ": " + str(ratedCourses[i][1]))

    conn.close()

query("SP25", "Deep learning and neural network training", False, False)




