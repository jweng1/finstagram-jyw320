#Import Flask Library
from flask import Flask, render_template, request, session, url_for, redirect
import pymysql.cursors
import mysql.connector
from mysql.connector import Error
import hashlib
from functools import wraps
import time
import os
from io import BytesIO


app = Flask(__name__, static_url_path='/static')
app.secret_key = 'secret key'


conn = pymysql.connect(host='localhost',
                       port = 8889,
                       user='root',
                       password='root',
                       database='finstagram',
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor,
                       autocommit=True)


def login_required(test):
    @wraps(test)
    def wrap(*args, **kwargs):
        if not "username" in session:
            return redirect(url_for("login"))
        return test(*args, **kwargs)
    return wrap

@app.route('/logout', methods=['GET'])
def logout():
    session.pop('username')
    return redirect('/')

#index function (home page)
@app.route('/')
def index():
    return render_template('index.html')

#register user
@app.route('/register', methods=['GET'])
def register():
    return render_template('register.html')

#register authentication
@app.route('/registerAuth', methods=['POST'])
def registerAuth():
    username =  request.form['username']
    plainPw = request.form['password']
    hashPw = hashlib.sha256(plainPw.encode('utf-8')).hexdigest()
    firstName = request.form['firstname']
    lastName = request.form['lastname']
    email = request.form['email']

    cursor = conn.cursor()
    check = 'SELECT * FROM Person WHERE username = %s'
    cursor.execute(check, (username))
    data = cursor.fetchone()
    error = None
    if(data):
        error = '%s is already taken.' % (username)
        return render_template('register.html', error=error)
    else:
        query = 'INSERT INTO Person VALUES (%s, %s, %s, %s, %s)'
        cursor.execute(query, (username, hashPw, firstName, lastName, email))
        cursor.close()
        return render_template('index.html')

#login function
@app.route('/login', methods=['GET'])
def login():
    return render_template('login.html')

#login authentication
@app.route('/loginAuth', methods=['POST'])
def loginAuth():
    username = request.form['username']
    plainPw = request.form['password']
    hashPw = hashlib.sha256(plainPw.encode('utf-8')).hexdigest()

    cursor = conn.cursor()
    query = 'SELECT * FROM Person WHERE username = %s and password = %s'
    cursor.execute(query, (username, hashPw))
    data = cursor.fetchone()
    cursor.close()
    error = None
    if(data):
        #create session for user
        session['username'] = username
        return redirect(url_for('home'))
    else:
        error = 'Invalid login or username'
        return render_template('login.html', error=error)

#user home page after sucessful log in
@app.route('/home')
@login_required
def home():
    return render_template('home.html', username=session['username'])


@app.route('/upload', methods=['GET'])
@login_required
def upload():
    #routes to upload photo
    return render_template('upload.html')

@app.route('/uploadPhoto', methods=['POST'])
@login_required
def uploadPhoto():
    imagefile = request.files['imageFile'].read()
    caption = request.form['caption']
    allFollowers = 0
    if request.form.getlist('allFollowers') != []:
        allFollowers = 1
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    
    cursor = conn.cursor()
    blobquery = 'INSERT INTO Photo (postingDate, picture, allFollowers, caption, poster) VALUES (%s, %s, %s, %s, %s)'
    blobtuple = (ts, imagefile, allFollowers, caption, session['username'])
    cursor.execute(blobquery, blobtuple)
    

    #don't share to all followers
    if allFollowers == 0:
        print('allFollowers = 0')
        cursor.execute("SELECT groupName FROM FriendGroup WHERE groupCreator=%s", session["username"])
        groupData = cursor.fetchall()
        return render_template("upload.html", allFollowers=False, groupData=groupData)
    
    cursor.close()
    message = "Image has been successfully uploaded."
    return render_template("upload.html", message=message)

@app.route('/share', methods=["POST"])
@login_required
def assignGroups():
    for group in request.form:
        selected = 0
        if request.form.getlist(group) != []:
            selected = 1
        
        cursor = conn.cursor()
        query1 = 'SELECT MAX(pID) FROM Photo WHERE allFollowers=0 AND poster=%s'
        cursor.execute(query1, session["username"])
        photoID = cursor.fetchall()
        photoID = photoID[0]['MAX(pID)']
        
        if selected == 1:
            query2 = 'INSERT INTO SharedWith (pID, groupName, groupCreator) VALUES (%s, %s, %s)'
            cursor.execute(query2, (photoID, group, session["username"]))
    
        cursor.close()
    message = "Image has been successfully uploaded."
    return render_template("upload.html", message=message)

@app.route("/followUser", methods=["POST"])
@login_required
def followUser():
    followerUsername = request.form["followUser"]
    try:
        cursor = conn.cursor()
        query = 'INSERT INTO Follow (follower, followee, followStatus) VALUES (%s, %s, %s)'
        cursor.execute (query, (session["username"], followerUsername, 0))
        message = "Request sent successfully"
        cursor.close()
        return render_template("home.html", message=message, username=session["username"])
    except:
        message = "Error following user"
        return render_template("home.html", message=message, username=session["username"])

@app.route("/followrequests", methods=["GET"])
@login_required
def followrequests():
    cursor = conn.cursor()
    query = 'SELECT * FROM Follow WHERE followee=%s AND followStatus=%s'
    cursor.execute(query, (session["username"], 0))
    followrequests = cursor.fetchall()
    cursor.close()
    
    if(followrequests):
        return render_template('followrequests.html', followrequests=followrequests)
    else:
        message = 'No requests at this time'
        return render_template('followrequests.html', followrequests=followrequests, message=message)


@app.route("/acceptFollow", methods=["POST"])
@login_required
def acceptFollow():
    followeeUsername = session["username"]
    query = 'SELECT follower FROM Follow WHERE followee=%s AND followStatus=%s'
    cursor = conn.cursor()
    cursor.execute(query, (followeeUsername, 0))
    data = cursor.fetchall()

    for follower in data:
        action = request.form["action" + follower["follower"]]
        if action == 'accept':
            query = 'UPDATE Follow SET followStatus=%s WHERE follower=%s AND followee=%s'
            cursor.execute(query, (1, follower["follower"], session["username"]))
        elif action == 'decline':
            query = 'DELETE FROM Follow WHERE follower = %s AND followee = %s'
            cursor.execute(query, (follower["follower"], session["username"]))
    return redirect(url_for('home'))



@app.route('/followsInfo', methods=['GET'])
@login_required
def followInfo():
    currentUser = session['username']
    query = "SELECT * FROM follow WHERE follower = %s"
    cursor = conn.cursor()
    cursor.execute(query, currentUser)
    following = cursor.fetchall()
    
    query = "SELECT * FROM follow WHERE followee = %s"
    cursor.execute(query, currentUser)
    followers = cursor.fetchall()
    cursor.close()
    return render_template("follows.html", followers=followers, following=following)


@app.route('/groups', methods=['GET'])
@login_required
def groups():
    currentUser = session['username']
    query = "SELECT * FROM FriendGroup WHERE groupCreator=%s"
    cursor = conn.cursor()
    cursor.execute(query, currentUser)
    ownedGroups = cursor.fetchall()

    queryt = 'SELECT * FROM BelongTo WHERE username=%s AND groupCreator!=%s'
    cursor.execute(queryt, (currentUser, currentUser))
    inGroups = cursor.fetchall()
    cursor.close()
    
    return render_template('groups.html', owned=ownedGroups, inGroups=inGroups)


@app.route("/createGroup", methods=["POST"])
@login_required
def createGroup():
    groupName = request.form['groupName']
    description = request.form['description']
    currentUser = session['username']

    cursor = conn.cursor()
    check = 'SELECT groupName FROM FriendGroup WHERE groupName=%s'
    cursor.execute(check, (groupName))
    data = cursor.fetchone()
    error = None
    #checks if group name is taken 
    if(data):
        error = '%s is already taken.' % (groupName)
        return render_template('home.html', error=error)
    else:
        query = 'INSERT INTO FriendGroup (groupName, groupCreator, description) VALUES (%s, %s, %s)'
        cursor.execute(query, (groupName, currentUser, description))

        queryt = 'INSERT INTO BelongTo (username, groupName, groupCreator) VALUES (%s, %s, %s)'
        cursor.execute(queryt, (currentUser, groupName, currentUser))
        cursor.close()

        message = "Close Friend Group successfully created!"
        return render_template("home.html", groupmessage=message, username=session["username"])
        
    message = "Error creating Friend Group"
    return render_template("home.html", groupmessage=message, username=session["username"])


@app.route("/addfriends", methods=["GET"])
@login_required
def addfriends():
    query = "SELECT groupname FROM FriendGroup WHERE groupCreator=%s"
    cursor = conn.cursor()
    cursor.execute(query, session["username"])
    data = cursor.fetchall()
    cursor.close()
    return render_template("addfriends.html", friendgroups=data)

@app.route('/addfriend', methods=["POST"])
@login_required
def addFriend():
    friend = request.form["friend"]
    select = request.form.get("grouplist")
   
    cursor = conn.cursor()
    query = "INSERT INTO BelongTo (username, groupName, groupCreator) VALUES (%s, %s, %s)"
    fetchquery = "SELECT groupName FROM FriendGroup WHERE groupCreator=%s"
    cursor.execute(fetchquery, session["username"])
    data = cursor.fetchall()
    cursor.execute(query, (friend, select, session["username"]))
    cursor.close()

    message = "Friend successfully added to Friend Group!"
    return render_template("addfriends.html", friendgroups=data, message=message)

def write_file(data, filename):
    with open(filename, 'wb') as file:
        file.write(data)

@app.route("/images", methods=["GET"])
@login_required
def images():
    query = "SELECT * FROM Photo WHERE allFollowers=1 OR poster=%s OR pID in (SELECT pID FROM SharedWith NATURAL JOIN BelongTo WHERE BelongTo.username=%s AND SharedWith.groupName = BelongTo.groupName) ORDER BY postingDate desc"
    cursor = conn.cursor()
    cursor.execute(query, (session["username"], session["username"]))
    
    data = cursor.fetchall()
    n = 0
    for i in data:
        n = i['pID']
        photoPath = '/Users/jweng/Desktop/finstagram/photoData/' + str(n) + '.jpeg'
        write_file(i['picture'], photoPath)


    cursor.close()
    return render_template("images.html", images=data)


#Run the app on localhost port 5000
#debug = True -> you don't have to restart flask
#for changes to go through, TURN OFF FOR PRODUCTION
#url for local host is '127.0.0.1'
if __name__ == "__main__":
    app.run('127.0.0.1', 5000, debug=True)
