from flask import Flask, render_template, request, redirect, jsonify
import os
import time
import pandas as pd
from langchain import ConversationChain
from chatbots import Chatbots, parse_output
from compare_rsids import compare_gene_conditions

os.environ['api_key'] = 'sk-proj-ezx7ZOuA3V5rEIYf82HgT3BlbkFJrHJOLc8D2zoZ4BbHAkrY'

# INITIALIZING APP, CHATBOTS AND MEMORY
if not os.path.exists('uploads'):
    os.makedirs('uploads')

app = Flask(__name__)

params = {'open_api_key': os.environ['api_key']}
chatbot = Chatbots(params)

if os.path.exists('static/audio.mp3'):
    os.remove('static/audio.mp3')

memory_loaded = False

# Initial prompt
chatbot.conversation_chain.predict(
    input="In this conversation, you are the world's best dermatologist. Your personality is knowledgeable, vibrant, empathetic, communicative, observant, as well as communicative. Engage users in a friendly and conversational manner about their health and lifestyle (diet, exercise, sleep, stress management, etc). IMPORTANT: Keep messages as concise as possible. Make sure to cite the specific rsid (GIVE THE SPECIFIC ONE, for example Rs1042602) that leads you to different diagnoses."
)
reply = parse_output(chatbot.chat_bot_memory.load_memory_variables({})['history'])

username = ""

@app.route("/username-endpoint", methods=["POST"])
def username_endpoint():
    global username, memory_loaded
    input = request.get_json()
    username = input.get("username")

    if not memory_loaded:
        chatbot.database_file_name = f"{username}_records.txt"
        chatbot.reading_history(chatbot.database_file_name)
        chatbot.initialize_chains()
        chatbot.memory_loaded = True
        memory_loaded = True
        return jsonify({"message": "Username loaded successfully."})
    else:
        return jsonify({"message": "Username already loaded."})

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        user_input = request.form["user_input"]
        chat_response = chatbot.get_response(user_input)
        response = chat_response['response']
        emotion_image_url = chat_response["emotion_img_url"]
        
        # TEXT TO SPEECH 
        chatbot.text_to_speech(response)

        data = {
            "messages": chatbot.messages,
            "emotion_image": emotion_image_url,
            "summary": chatbot.current_summary
        }
        return render_template("index.html", data=data, response=response)
    else:
        default_message = {
            "role": "assistant",
            "content": "Hello! How can I assist you today?",
            "time": time.ctime(time.time()),
            "emotion_image": chatbot.emotion_avatars["neutral"]
        }
        data = {
            "messages": chatbot.messages if chatbot.messages else [default_message],
            "emotion_image": chatbot.messages[-1]["emotion_image"] if chatbot.messages else default_message["emotion_image"],
            "summary": chatbot.current_summary
        }
        return render_template("index.html", data=data)

@app.route('/user_image', methods=['POST'])
def user_image():
    if 'userImageFile' not in request.files:
        return 'No file part', 400

    file = request.files['userImageFile']
    if file.filename == '':
        return 'No selected file', 400

    file.save(os.path.join('uploads', username, file.filename))
    return 'File uploaded successfully', 200

@app.route('/genomic_data', methods=['POST'])
def upload_genomic_data():
    if 'genomicFile' not in request.files:
        return 'No file part', 400

    file = request.files['genomicFile']
    if file.filename == '':
        return 'No selected file', 400

    file_path = os.path.join("uploads", file.filename)
    file.save(file_path)

    compare_gene_conditions(file_path, 'gene_conditions.csv')

    conditions_input = ""
    res = pd.read_csv('gene_conditions.csv')
    for _, row in res.iterrows():
        conditions_input += f'{row["ID"]} causes {row["Summary"]}. '

    chatbot.conversation_chain.predict(
        input=f"My conditions due to my genomic data are as follows: {conditions_input}"
    )

    return 'File uploaded and analyzed successfully', 200

@app.route('/generate_image', methods=['POST'])
def generate_emotion_images():
    user_prompt = request.form['user_input']
    images = chatbot.generate_all_emotion_images(user_prompt)
    return jsonify(images)

@app.route('/process_genomic_data', methods=['POST'])
def process_genomic_data():
    if 'genomicFile' not in request.files:
        return 'No file part', 400

    file = request.files['genomicFile']
    if file.filename == '':
        return 'No selected file', 400

    file_path = os.path.join("uploads", file.filename)
    file.save(file_path)

    conditions_results = compare_gene_conditions(file_path, 'gene_conditions.csv')
    conditions_input = ", ".join(conditions_results)

    chatbot.conversation_chain.predict(
        input=f"My conditions due to my genomic data are as follows: {conditions_input}"
    )

    return 'File uploaded and analyzed successfully', 200

if __name__ == "__main__":
    app.run("0.0.0.0")
