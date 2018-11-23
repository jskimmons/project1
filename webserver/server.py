#!/usr/bin/env python2.7

"""
Columbia W4111 Intro to databases
Example webserver

To run locally

    python server.py

Go to http://localhost:8111 in your browser


A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""

import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, session, escape, flash

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)



# XXX: The Database URI should be in the format of: 
#
#     postgresql://USER:PASSWORD@<IP_OF_POSTGRE_SQL_SERVER>/<DB_NAME>
#
# For example, if you had username ewu2493, password foobar, then the following line would be:
#
#     DATABASEURI = "postgresql://ewu2493:foobar@<IP_OF_POSTGRE_SQL_SERVER>/postgres"
#
# For your convenience, we already set it to the class database

# Use the DB credentials you received by e-mail
DB_USER = "erc2181"
DB_PASSWORD = "n9eqzfk3"

DB_SERVER = "w4111.cisxo09blonu.us-east-1.rds.amazonaws.com"

DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/w4111"


#
# This line creates a database engine that knows how to connect to the URI above
#
engine = create_engine(DATABASEURI)

# generate secret key for use with sessions
app.secret_key = os.urandom(12)


# Here we create a test table and insert some values in it
# engine.execute("""DROP TABLE IF EXISTS test;""")


@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request 
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request

  The variable g is globally accessible
  """
  try:
    g.conn = engine.connect()
  except:
    print "uh oh, problem connecting to database"
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass

@app.route('/')
def index():

  # if user not logged in, redirect them to login
  if not session.get('logged_in'):
    return render_template('login.html')

  # example of context
  cmd = "SELECT * FROM subpages"
  cursor = g.conn.execute(text(cmd))
  subpage_tups = []
  for result in cursor:
  	sub_tup = (result["sid"], result["sp_name"], result["description"])
  	subpage_tups.append(sub_tup)
  context = dict(user = session['username'], subpages = subpage_tups)

  # render index.html for a given user
  return render_template("index.html", **context)

@app.route('/logout', methods=['GET'])
def logout():
  session.pop('username')
  session.pop('uid')
  session['logged_in'] = False
  return redirect('/')

@app.route('/login', methods=['POST', 'GET'])
def login():
    
    # logic to check if a username / password combo is valid
    # plaintext for now

    check_pswd =  'select exists ( \
                   select * \
                   from users \
                   where \
                   user_name = \'' + request.form['username'] + '\' and \
                   password = \'' + request.form['password'] + '\');';
    
    cursor = g.conn.execute(text(check_pswd))
    result_lst = []
    for result in cursor:
      result_lst.append(result['exists'])
    cursor.close()

    # allow user to access their homepage if they are logged in
    if result_lst[0]:
      session['logged_in'] = True
      session['username'] = request.form['username']

      getuid_cmd = 'select uid from users where user_name = \'{}\';'.format(session['username'])
      cursor = g.conn.execute(text(getuid_cmd))
      session['uid'] = cursor.first()['uid']

      return redirect('/')
    else:
      return render_template('login.html')


# render a page to create a new user
@app.route('/newuser', methods=['GET'])
def newuser():
  return render_template("newuser.html")

# render a page to create a new subpage
@app.route('/newsubpage', methods=['GET'])
def newsubpage():
  return render_template("newsubpage.html")


# logic to add new user to a database
@app.route('/adduser', methods=['POST'])
def adduser():
  username = request.form['username']
  password = request.form['password']
  email = request.form['email']
  dob = request.form['dob']
  confirmpass = request.form['confirmpass']

  if password != confirmpass:
    flash("Passwords do not match!")
    return redirect('/newuser')

    # TODO maybe check username already used? email too?

  cmd = 'INSERT INTO users(user_name, password, email, dob) VALUES (:username1, :password1, :email1, :dob1)';
  g.conn.execute(text(cmd), username1 = username, password1 = password, email1 = email, dob1 = dob);

  session['username'] = username
  
  getuid_cmd = 'select uid from users where user_name = \'{}\';'.format(session['username'])
  cursor = g.conn.execute(text(getuid_cmd))
  
  session['uid'] = cursor.first()['uid']

  session['logged_in'] = True

  return redirect('/')

# TODO add subpage view with list of all posts in a subpage
@app.route('/subpage/', methods=['GET'])
def subpage():

  # get sid of subpage trying to generate
  sid = request.args.get('sid')

  # query for all posts in this sid
  cmd = 'SELECT p.title, p.body, u.user_name FROM post p, users u WHERE p.uid = u.uid and p.sid = {};'.format(sid);
  cursor = g.conn.execute(text(cmd));

  posts = []
  for result in cursor:
    posts.append((result['title'], result['body'], result['user_name']))

  cmd = 'SELECT sp_name, description FROM subpages WHERE sid = {};'.format(sid);
  cursor = g.conn.execute(text(cmd));

  results = cursor.first()

  subpage_title = results['sp_name']
  subpage_desc = results['description']

  context = dict(posts=posts, subpage_title=subpage_title, subpage_desc=subpage_desc, sid=sid)

  return render_template("subpage.html", **context)

# TODO add user view with list of all posts in a subpage
@app.route('/user/', methods=['GET'])
def user():

  # get sid of subpage trying to generate
  uid = request.args.get('uid')

  # query for all posts in this sid
  cmd = 'SELECT p.title, p.body, s.sp_name FROM post p, subpages s WHERE p.sid = s.sid and p.uid = {}'.format(uid);
  cursor = g.conn.execute(text(cmd), uid1 = uid);

  posts = []
  for result in cursor:
    posts.append((result['title'], result['body'], result['sp_name']))

  cmd = 'SELECT * FROM users WHERE uid = {}'.format(uid);
  cursor = g.conn.execute(text(cmd), uid1 = uid);

  results = cursor.first()
  user_name = results['user_name']

  context = dict(posts=posts, user_name = user_name, uid=uid)

  return render_template("user.html", **context)

@app.route('/followSubpage/', methods=['POST'])
def followSubpage():
  sid = request.args.get('sid')
  uid = session['uid']

  insert_follow_cmd = 'INSERT INTO follows(sid, uid) VALUES (:sid1, :uid1)';
  g.conn.execute(text(insert_follow_cmd), sid1 = sid, uid1 = uid);
  return redirect('/subpage/?sid={}'.format(sid))

# logic to add new user to a database
@app.route('/addpost/', methods=['POST'])
def addpost():
  uid = session['uid']
  sid = request.args.get('sid')
  title = request.form['title']
  body = request.form['body']

  cmd = 'INSERT INTO post(uid, sid, title, body, date_posted) VALUES ({}, {}, \'{}\', \'{}\', now())'.format(uid, sid, title, body);
  g.conn.execute(text(cmd));

  return redirect('/subpage/?sid={}'.format(sid))

# logic to add new user to a database
@app.route('/addsubpage', methods=['POST'])
def addsubpage():
  sp_name = request.form['sp_name']
  description = request.form['description']

  cmd = 'INSERT INTO subpages(sp_name, description) VALUES (\'{}\', \'{}\')'.format(sp_name, description);
  g.conn.execute(text(cmd));

  return redirect('/')

if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using

        python server.py

    Show the help text using

        python server.py --help

    """

    HOST, PORT = host, port
    print "running on %s:%d" % (HOST, PORT)
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


  run()
