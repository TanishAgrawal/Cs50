import os

import sqlite3
from datetime import date, datetime
from flask import Flask, flash, redirect, render_template, request, session
from flask.helpers import url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = '3cab074c0345d7e29495a481b81a6f1576ca3f8551a87372'

app.config["TEMPLATES_AUTO_RELOAD"] = True


@app.route("/", methods=["POST", "GET"])
def index():
    #checks if the user is logged in or not and if not redirects them back to login
    if not 'user_id' in session:
        return redirect(url_for("login"))
    #gets the user_id to get the tasks of the user
    id = session["user_id"]
    con = get_db_connection()
    work = con.execute('''SELECT id,task,description,deadline,priority from WORK WHERE user_id = ? ORDER BY (CASE priority WHEN "Very Important" 
                THEN 1 WHEN "Important" 
                THEN 2 WHEN "Not So Important" 
                Then 3 END)''',(id,)).fetchall()
    con.close()

    return render_template("index.html", work=work)

@app.route('/delete/<int:id>',  methods=["POST", "GET"])
def delete_task(id):
    
    if request.method == "POST":
        #we get the id of the task which we want to delete and then delete it from the database
        con = get_db_connection()
        con.execute("DELETE FROM work WHERE id = ?",(id,))
        con.commit()
        con.close
        if request.form.get("delete") == "Yes":
            flash("Done!!")

        else:
            #we can flash by using the flash function which was implemented in layout.html
            flash("Task Deleted!!")
            
    return redirect(url_for("index"))


@app.route("/add", methods=["POST", "GET"])
def add():
    if not 'user_id' in session:
        return redirect(url_for("login"))

    #we can pass the error which will be flashed in the html page by first setting it to none
    error = None

    #Getting all the values from the add form 
    description = request.form.get("description") 
    task = request.form.get("task")
    deadline = request.form.get("deadline")
    priority = request.form.get("priority")
    #we use the date.today function to get the date in which it was assigned 
    date_assigned = date.today()
    user = session["user_id"]

    #if the form was submitted we execute the following tasks
    if request.method == 'POST':

        if request.form.get("add") == "cancel":
            return redirect(url_for("index"))
        else:
            #we check if any input was left out 
            if not request.form.get("description") or not request.form.get("task"):
                error = 'Please Fill All Required Information'
            else:
                if request.form.get("deadline"):
                    """we cannot pass an empty string to the function which inverts the string thats why first we check
                        wheather the optional input was filled or not and then invert it"""
                    deadline = datetime.strptime( deadline, '%Y-%m-%d').strftime('%d-%m-%Y')

                #insert all the data which we get from the add form 
                con = get_db_connection()
                con.execute("INSERT INTO work(task,description,deadline,date_assigned,priority, user_id) VALUES (?,?,?,?,?,?)",(task,description,deadline,date_assigned,priority,user,))
                con.commit()
                con.close()
                
                flash("Task Added Successfully!!")
                return redirect(url_for("index"))

    #if there was an error we pass it to the html file to flash it 
    return render_template("add.html", error=error)

@app.route("/login", methods=["GET","POST"])
def login():

    #we clear all the previos sessions 
    session.clear()
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        #checking if all the imformation was filled or not
        if not request.form.get("password") or not request.form.get("username"):
            error="Username/Password not filled"
            return render_template("login.html", error=error)
        
        con = get_db_connection()
        
        #we get the username and the hashed password
        user = con.execute("Select id,name,password FROM users WHERE name = ?",(username,)).fetchall()
        
        #if the username is incorrect the length of "user" will be zero and hence the username would be wrong 
        #and if the passowrd is wrong we will display and error
        if len(user) != 1 or not check_password_hash(user[0][2], password):
                error = "username or password is incorrect"
                return render_template("login.html", error=error)
        if request.form.get("remember"):
            #this makes the user logged in permanently when the remember me checkbox is clicked
            session.permanent = True

        #configuring the session to current user 
        session["user_id"] = user[0][0]
        session["username"] = user[0][1]
        flash("Logged In!!")
        return redirect(url_for("index"))
        
    return render_template("login.html", error=error)

@app.route("/register", methods=["POST", "GET"])
def registration():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        con = get_db_connection()
        password_check = request.form.get("password_check")
        if not request.form.get("username") or not request.form.get("password") or not request.form.get("password_check"):
            error = "Please Fill All Required Information"
            return render_template("registration.html", error=error)
         
        username_check = con.execute("Select id FROM users WHERE name = ?",(username,)).fetchall()
        
        #looking for the same username and if there is someone with the same username the len of username_check will be 1
        if len(username_check) == 1:
            error = "Username Already Taken!"
            return render_template("registration.html", error=error)
        
        #checking if the password matches with the confirmation
        if password != password_check:
            error = "Passwords Don't Match!"
            return render_template("registration.html", error=error)
        
        #it generates the hash of the password for saftey purposes
        hash_pass = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
        con.execute("INSERT INTO users(name, password) VALUES(?,?)",(username,hash_pass,))
        con.commit()
        
        #getting the user id to configure the session
        username_check = con.execute("Select id,name FROM users WHERE name = ?",(username,)).fetchall()
        con.close()
        
        if request.form.get("remember"):
            session.permanent = True

        session["user_id"] = username_check[0][0]
        session["username"] = username_check[0][1]

        flash("Logged In")
        return redirect(url_for("index"))
        
    return render_template("registration.html", error=error)

#we get the id of the task which we want to update and then update it as we want
@app.route("/update/<int:id>", methods=["POST", "GET"])
def update(id): 
    description = request.form.get("description") 
    task = request.form.get("task")
    deadline = request.form.get("deadline")
    priority = request.form.get("priority")
    
    con = get_db_connection()
    work = con.execute("SELECT id,task,description,deadline,priority FROM work WHERE id = ?", (id,)).fetchall()
    deadline_inverted = datetime.strptime( work[0][3], '%d-%m-%Y').strftime('%Y-%m-%d')

    if request.method == "POST":
        
        if request.form.get("update") == "cancel":
            return redirect(url_for("index"))
        else:
            if request.form.get("deadline"):
                    deadline = datetime.strptime( deadline, '%Y-%m-%d').strftime('%d-%m-%Y')
            
            con.execute("UPDATE work SET task = ?,description = ?,deadline = ?,priority = ? WHERE id = ?", (task,description,deadline,priority,id,))
            con.commit()
            con.close()
            flash("Task Updated!!")
            return redirect(url_for("index"))
    
    return render_template("update.html", work=work, deadline_inverted=deadline_inverted)

@app.route("/ChangePassword", methods=["POST", "GET"])
def change_password():
    error = None
    old_password = request.form.get("old_password")
    password = request.form.get("password")
    password_check = request.form.get("password_check")
    id = session["user_id"]
    
    con = get_db_connection()
    user = con.execute("SELECT password FROM users WHERE id = ?", (id,)).fetchall()
    
    if request.method == "POST":

        if request.form.get("add") == "cancel":
            return redirect(url_for("index"))
        
        else:

            if not request.form.get("old_password") or not request.form.get("password") or not request.form.get("password_check"):
                error = "Please Fill All The Information"
                return render_template("change_password.html", error=error)
            
            #if the old password matches with the new one it will display an error
            if not check_password_hash(user[0][0], old_password):
                error = "Old Password Is Wrong"
                return render_template("change_password.html", error=error)
            
            if old_password == password_check:
                error = "Previous Password is same as the new"
                return render_template("change_password.html", error=error)
            if password != password_check:
                error = "Passwords Don't Match"
                return render_template("change_password.html", error=error)
            
            #it hashes the new password and inserts it into the database
            hash_pass = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
            
            con.execute("UPDATE users SET password = ? WHERE id = ?", (hash_pass, id,))
            con.commit()
            con.close()
            flash("Password Changed")
            return redirect(url_for("index"))
    return render_template("change_password.html", error=error)

@app.route("/logout")
def logout(): 
    #by clearing the session the user will be logged out
    session.clear()
    flash("Logged Out!!")
    return redirect(url_for("index"))
    
@app.route("/contact")
def contact_us(): 
    return render_template("contact_us.html")

@app.route("/about")
def about():
    return render_template("about.html")

def get_db_connection():
    #the connection the database was needed many times so this function provided the connection to the database 
    con = sqlite3.connect('task.db')
    con.row_factory = sqlite3.Row
    return con

if __name__ == "__main__":
    app.run(debug=True)