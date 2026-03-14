from flask import Flask, request, session, render_template_string
from flask_socketio import SocketIO, emit
import sqlite3
import requests

app = Flask(__name__)
app.secret_key = "ai_chat_secret"
socketio = SocketIO(app)

online_users = {}

# GEMINI API KEY
API_KEY = "YOUR_GEMINI_API_KEY"

# DATABASE
def db():
    conn = sqlite3.connect("chat.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():

    conn = db()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS messages(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender TEXT,
    receiver TEXT,
    message TEXT
    )
    """)

    conn.commit()
    conn.close()

# AI RESPONSE
def ask_ai(question):

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={API_KEY}"

    data = {
        "contents":[{"parts":[{"text":question}]}]
    }

    r = requests.post(url,json=data)

    try:
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return "AI response error"

# UI
page = """

<!DOCTYPE html>
<html>

<head>

<title>AI Chat Server</title>

<script src="https://cdn.socket.io/4.5.0/socket.io.min.js"></script>

<style>

body{
font-family:Arial;
background:#ece5dd;
}

#login{
width:300px;
margin:auto;
margin-top:100px;
}

#chat{
display:flex;
height:600px;
}

#users{
width:220px;
background:white;
border-right:1px solid gray;
padding:10px;
}

#messages{
flex:1;
background:#dcf8c6;
padding:10px;
overflow:auto;
}

.msg{
background:white;
margin:5px;
padding:6px;
border-radius:6px;
}

</style>

</head>

<body>

<div id="login">

<h2>AI Chat</h2>

<input id="username" placeholder="username"><br>
<input id="password" placeholder="password"><br>

<button onclick="login()">Login</button>
<button onclick="register()">Register</button>

</div>

<div id="chat" style="display:none">

<div id="users"></div>

<div style="flex:1">

<div id="messages"></div>

<input id="to" placeholder="Send To (user or AI)">
<input id="msg" placeholder="message">

<button onclick="send()">Send</button>

</div>

</div>

<script>

var socket = io()

socket.on("users",function(data){

document.getElementById("users").innerHTML =
"<h3>Online</h3>"+data.join("<br>")+"<br><br><b>AI</b>"

})

socket.on("receive",function(data){

var m = document.getElementById("messages")

m.innerHTML +=
"<div class='msg'><b>"+data.sender+"</b>: "+data.message+"</div>"

})

function register(){

fetch("/register",{

method:"POST",

headers:{"Content-Type":"application/json"},

body:JSON.stringify({

username:username.value,
password:password.value

})

})

}

function login(){

fetch("/login",{

method:"POST",

headers:{"Content-Type":"application/json"},

body:JSON.stringify({

username:username.value,
password:password.value

})

}).then(r=>r.json()).then(d=>{

if(d.success){

login.style.display="none"
chat.style.display="flex"

}

})

}

function send(){

socket.emit("send",{

to:to.value,
message:msg.value

})

msg.value=""

}

</script>

</body>

</html>

"""

@app.route("/")
def home():
    return render_template_string(page)

@app.route("/register",methods=["POST"])
def register():

    data=request.json

    conn=db()

    try:

        conn.execute(
        "INSERT INTO users(username,password) VALUES(?,?)",
        (data["username"],data["password"]))

        conn.commit()

        return {"success":True}

    except:

        return {"success":False}

@app.route("/login",methods=["POST"])
def login():

    data=request.json

    conn=db()

    user=conn.execute(
    "SELECT * FROM users WHERE username=? AND password=?",
    (data["username"],data["password"])).fetchone()

    if user:

        session["username"]=data["username"]

        return {"success":True}

    return {"success":False}

@socketio.on("connect")
def connect():

    username=session.get("username")

    if username:

        online_users[username]=request.sid

        emit("users",list(online_users.keys()),broadcast=True)

@socketio.on("send")
def send(data):

    sender=session.get("username")

    receiver=data["to"]

    message=data["message"]

    # AI CHAT
    if receiver.lower()=="ai":

        ai_reply=ask_ai(message)

        emit("receive",{
            "sender":"AI",
            "message":ai_reply
        },room=online_users[sender])

        return

    if receiver in online_users:

        emit(
        "receive",
        {
            "sender":sender,
            "message":message
        },
        room=online_users[receiver]
        )

if __name__=="__main__":

    init_db()

    socketio.run(app,debug=True)