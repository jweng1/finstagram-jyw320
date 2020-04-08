#add friends function 
def addfriends():
    query = "SELECT groupname FROM closefriendgroup WHERE groupOwner=%s"
    with connection.cursor() as cursor:
        cursor.execute(query, session["username"])
    data = cursor.fetchall()
    return render_template("addfriends.html", closefriendgroups=data)
    
# add group function
def groups():
    current_user = session["username"]
    query = "SELECT * FROM CloseFriendGroup WHERE groupOwner = %s"
    with connection.cursor() as cursor:
        cursor.execute(query, current_user)
    owned_groups = cursor.fetchall()
    query = "SELECT * FROM Belong WHERE username = %s AND groupOwner != %s"
    with connection.cursor() as cursor:
        cursor.execute(query, (current_user, current_user))
    in_groups = cursor.fetchall()
    return render_template("groups.html", owned=owned_groups, in_groups=in_groups)
