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
# Comment

import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool, exc
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

def get_uid(username):

  cmd = "SELECT uid FROM users WHERE user_name=:username";
  cursor = g.conn.execute(text(cmd), username=username)
  
  user_id = 0
  for result in cursor:
    user_id = result["uid"]
  return user_id

@app.route('/')
def index():

  # if user not logged in, redirect them to login
  if not session.get('logged_in'):
    return render_template('login.html')

  curr_user = session['username']
  user_id = get_uid(curr_user)

  cmd = "SELECT sid, sp_name, description "\
  		"FROM subpages NATURAL JOIN follows "\
  		"WHERE uid=:uid1";
  cursor = g.conn.execute(text(cmd), uid1=user_id)
  subpage_tups = []
  for result in cursor:
  	sub_tup = (result["sid"], result["sp_name"], result["description"])
  	subpage_tups.append(sub_tup)

  cmd = "SELECT sid, sp_name, description FROM subpages WHERE sid NOT IN ("\
        "SELECT sid FROM subpages NATURAL JOIN follows WHERE uid=:uid1)";
  cursor = g.conn.execute(text(cmd), uid1=user_id)
  rest = []
  for result in cursor:
    rest_tup = (result["sid"], result["sp_name"], result["description"])
    rest.append(rest_tup)
  	
  context = dict(user = session['username'], user_id = user_id, subpages = subpage_tups, rest = rest)

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

    given_username = request.form['username']
    given_pswd = request.form['password']

    check_pswd =  'select exists (select * from users where user_name=:username and password=:password);';
    cursor = g.conn.execute(text(check_pswd), username=given_username, password=given_pswd);

    result_lst = []
    for result in cursor:
      result_lst.append(result['exists'])
    cursor.close()

    # allow user to access their homepage if they are logged in
    if result_lst[0]:
      session['logged_in'] = True
      session['username'] = request.form['username']

      getuid_cmd = 'select uid from users where user_name=:username';
      cursor = g.conn.execute(text(getuid_cmd), username=given_username);
      session['uid'] = cursor.first()['uid']

      return redirect('/')
    else:
      return render_template('login.html')


# render a page to create a new user
@app.route('/newuser', methods=['GET'])
def newuser(integrity_error=0, date_error=0, no_username=0, no_pswd=0, no_conf=0, no_email=0):
  context = dict(integrity_error=integrity_error, date_error=date_error, no_username=no_username, no_pswd=no_pswd, no_conf=no_conf, no_email=no_email)
  return render_template("newuser.html", **context)

# logic to add new user to a database
@app.route('/adduser', methods=['POST'])
def adduser():
  username = request.form['username']
  password = request.form['password']
  email = request.form['email']
  dob = request.form['dob']
  confirmpass = request.form['confirmpass']

  if username == '':
    return newuser(no_username=1)
  if password == '':
    return newuser(no_pswd=1)
  if confirmpass == '':
    return newuser(no_conf=1)
  if email == '':
    return newuser(no_email=1)
    
  if password != confirmpass:
    flash("Passwords do not match!")
    return redirect('/newuser')

    # TODO maybe check username already used? email too?
  try:
    cmd = 'INSERT INTO users(user_name, password, email, dob) VALUES (:username1, :password1, :email1, :dob1)';
    g.conn.execute(text(cmd), username1 = username, password1 = password, email1 = email, dob1 = dob);
  except exc.IntegrityError as e:
    return newuser(integrity_error=1)
  except exc.DataError as e:
    return newuser(date_error=1)

  session['username'] = username
  
  getuid_cmd = 'select uid from users where user_name=:username';
  
  try:
    cursor = g.conn.execute(text(getuid_cmd), username=session['username'])
  except exc.IntegrityError as e:
    print("data already exists")
    redirect('/')
  
  session['uid'] = cursor.first()['uid']

  session['logged_in'] = True

  return redirect('/')

# TODO add subpage view with list of all posts in a subpage
@app.route('/subpage/', methods=['GET'])
def subpage():

  # get sid of subpage trying to generate
  sid = request.args.get('sid')
  uid = session['uid']

  # query for all posts in this sid
  
  # cmd = 'SELECT p.title, p.body, u.user_name, u.uid FROM post p, users u WHERE p.uid = u.uid and p.sid = {};'.format(sid);

  # gets all posts ordered by number of votes
  cmd = '''
          select p.title, p.body, u.uid, u.user_name, p.pid, count(v.*) as vote_count
          from post p left outer join vote v on p.pid = v.pid, users u
          where p.uid = u.uid and p.sid = :sid
          group by p.pid, p.title, p.body, u.uid, u.user_name
          order by count(v.*) desc;
        ''';

  cursor = g.conn.execute(text(cmd), sid=sid);

  posts = []
  for result in cursor:
    if result['user_name'] == session['username']:
      my_post = True
    else:
      my_post = False
    posts.append((result['title'], result['body'], result['user_name'], result['uid'], result['pid'], result['vote_count'], my_post))

  cmd = 'SELECT sp_name, description FROM subpages WHERE sid = :sid';
  cursor = g.conn.execute(text(cmd), sid=sid);

  results = cursor.first()

  subpage_title = results['sp_name']
  subpage_desc = results['description']

  cmd = 'SELECT sp_name, description FROM subpages WHERE sid = :sid';
  cursor = g.conn.execute(text(cmd), sid=sid);

  results = cursor.first()

  subpage_title = results['sp_name']
  subpage_desc = results['description']

  cmd = 'Select exists (select * from follows where sid=:sid and uid=:uid)';
  cursor = g.conn.execute(text(cmd), sid=sid, uid=uid);
  results = cursor.first()
  already_following = results['exists']

  context = dict(posts=posts, subpage_title=subpage_title, subpage_desc=subpage_desc, sid=sid, already_following=already_following)

  return render_template("subpage.html", **context)

@app.route('/post/', methods=['GET'])
def post():

  curr_user = session['username']
  user_id = get_uid(curr_user)

  pid = request.args.get('pid')

  cmd = "SELECT * FROM post WHERE pid = :pid";
  cursor = g.conn.execute(text(cmd), pid=pid);
  post = 0
  for result in cursor:
    post = (result['pid'], result['sid'], result['uid'], result['date_posted'], result['title'], result['body'])

  cmd = "SELECT * FROM comments WHERE pid = :pid";
  cursor = g.conn.execute(text(cmd), pid=pid);
  comments = []
  for result in cursor:
    comments.append((result['cid'], result['pid'], result['uid_post'], result['date_posted'], result['body']))

  users = {}
  for i in range(len(comments)):
    comment = comments[i]
    uid = comment[2]
    cmd = "SELECT user_name FROM users WHERE uid = :uid";
    cursor = g.conn.execute(text(cmd), uid=uid)
    user_name = 0
    for result in cursor:
      user_name = result['user_name']
    if user_name not in users:
      users[uid] = user_name

  context = dict(user = session['username'], curr_uid = user_id, post = post, comments = comments, users = users)

  return render_template("post.html", **context)

@app.route('/addcomment/', methods=['POST'])
def addcomment():

  pid = request.args.get("pid")
  uid_post = request.args.get("uid_post")
  comment = request.form["comment"]
  # comment = comment.replace("\'", "\'\'")

  cmd = 'INSERT INTO comments(cid, pid, uid_post, date_posted, body) VALUES (nextval(\'comment_sequence\'), :pid, :uid_post, now(), :comment)';
  g.conn.execute(text(cmd), pid=pid, uid_post=uid_post, comment=comment);

  return redirect(request.referrer)

@app.route('/delcomment/', methods=['POST'])
def delcomment():

  cid = request.args.get("cid")

  cmd = 'DELETE FROM comments WHERE cid = :cid';
  g.conn.execute(text(cmd), cid=cid);

  return redirect(request.referrer)

@app.route('/dm_threads/', methods=['GET'])
def dm_threads(local_var=0, local_uid=0, exists_issue=0):

  uid = 0
  if not local_var:
    uid = request.args.get("uid")
  else:
    uid = local_uid

  cmd = """WITH uid_did(uid, did) AS (
        SELECT uid_receiver AS uid, did FROM dm_sent NATURAL JOIN dm_recv 
        WHERE uid_sender = :uid1
        UNION
        SELECT uid_sender AS uid, did FROM dm_sent NATURAL JOIN dm_recv
        WHERE uid_receiver = :uid2
        ORDER BY did),
        usr_extract(uid, did, user_name, dob, email, password) AS (
        SELECT DISTINCT ON (S.uid) * FROM uid_did S NATURAL JOIN users)
        SELECT * FROM usr_extract ORDER BY did DESC;"""
  cursor = g.conn.execute(text(cmd), uid1 = uid, uid2 = uid)
  threads = []
  for result in cursor:
    user_id = result['uid']
    did = result['did']
    username = result['user_name']
    row_tup = (user_id, did, username)
    threads.append(row_tup)

  context = dict(user=session['username'], user_id=get_uid(session['username']), threads=threads, exists_issue=exists_issue)

  return render_template("threads.html", **context)

@app.route('/indi_thread/', methods=['GET'])
def indi_thread():

  uid_other = request.args.get("uid")
  uid_me = get_uid(session['username'])

  my_name = session['username']
  other_name = 0
  cmd = "SELECT user_name FROM users WHERE uid = :uid_other";
  cursor = g.conn.execute(text(cmd), uid_other=uid_other);
  for result in cursor:
    other_name = result['user_name']

  cmd = """SELECT * FROM dm_sent NATURAL JOIN dm_recv
  WHERE uid_sender = :uid_me1 AND uid_receiver = :uid_other1
  UNION
  SELECT * FROM dm_sent NATURAL JOIN dm_recv
  WHERE uid_sender = :uid_other2 AND uid_receiver = :uid_me2
  ORDER BY did LIMIT 12;
  """
  cursor = g.conn.execute(text(cmd), uid_me1=uid_me, uid_other1=uid_other, uid_other2=uid_other, uid_me2=uid_me)
  messages = []
  for result in cursor:
    if result['uid_sender'] == uid_me:
      messages.append((my_name, result['body']))
    else:
      messages.append((other_name, result['body']))

  context = dict(user=session['username'], messages=messages, other=other_name, uid_other=uid_other, uid_me=uid_me)

  return render_template("indi_thread.html", **context)

@app.route('/send_dm/', methods=['POST'])
def send_dm():

  uid_sender = request.args.get("uid_sender")
  uid_receiver = request.args.get("uid_receiver")
  body = request.form["message"]
  # body = body.replace("\'", "\'\'")

  cmd = "INSERT INTO dm_sent(uid_sender, body, time_sent) VALUES (:uid_sender, :body, now())".format(uid_sender, body)
  g.conn.execute(text(cmd), uid_sender=uid_sender, body=body);

  did = 0
  cmd = "SELECT did FROM dm_sent WHERE uid_sender = :uid_sender ORDER BY did DESC LIMIT 1";
  cursor = g.conn.execute(text(cmd), uid_sender=uid_sender)
  for result in cursor:
    did = result['did']

  cmd = "INSERT INTO dm_recv(uid_receiver, uid_sender, did, time_received) VALUES (:uid_receiver, :uid_sender, :did, now())";
  g.conn.execute(text(cmd), uid_receiver=uid_receiver, uid_sender=uid_sender, did=did);

  return redirect(request.referrer)


@app.route('/create_thread/', methods=['POST'])
def create_thread():

  uid_sender = request.args.get("uid_sender")
  recipient = request.form["recipient"]
  message = request.form["new_msg"]
  message = message.replace("\'", "\'\'")

  cmd = "SELECT uid, user_name FROM users WHERE user_name = :recipient";
  cursor = g.conn.execute(text(cmd), recipient=recipient)
  user = cursor.fetchall()
  exists = len(user)
  if exists:
    uid_receiver = user[0]["uid"]

    cmd = "INSERT INTO dm_sent(uid_sender, body, time_sent) VALUES (:uid_sender, :message, now())";
    g.conn.execute(text(cmd), uid_sender=uid_sender, message=message);

    did = 0
    cmd = "SELECT did FROM dm_sent WHERE uid_sender = :uid_sender ORDER BY did DESC LIMIT 1";
    cursor = g.conn.execute(text(cmd), uid_sender=uid_sender);
    for result in cursor:
      did = result['did']

    cmd = "INSERT INTO dm_recv(uid_receiver, uid_sender, did, time_received) VALUES (:uid_receiver, :uid_sender, :did, now())";
    g.conn.execute(text(cmd), uid_receiver=uid_receiver, uid_sender=uid_sender, did=did);

    return redirect(request.referrer)

  else:
    
    return dm_threads(local_var=1, local_uid=uid_sender, exists_issue=1)

# TODO add user view with list of all posts in a subpage
@app.route('/user/', methods=['GET'])
def user():

  # get sid of subpage trying to generate
  uid = request.args.get('uid')

  # query for all posts in this sid
  # cmd = 'SELECT p.title, p.body, s.sp_name, s.sid FROM post p, subpages s WHERE p.sid = s.sid and p.uid = :uid';

  cmd = '''
          select p.title, p.body, s.sp_name, s.sid, p.pid, count(v.*) as vote_count
          from post p left outer join vote v on p.pid = v.pid, subpages s
          where p.sid = s.sid and p.uid = :uid
          group by p.pid, p.title, p.body, s.sid, s.sp_name
          order by count(v.*) desc;
        ''';
  
  cursor = g.conn.execute(text(cmd), uid=uid);

  posts = []
  for result in cursor:
    posts.append((result['title'], result['body'], result['sp_name'], result['sid'], result['pid'], result['vote_count']))

  cmd = 'SELECT * FROM users WHERE uid = :uid';
  cursor = g.conn.execute(text(cmd), uid=uid);

  results = cursor.first()
  user_name = results['user_name']

  context = dict(posts=posts, user_name = user_name, uid=uid)

  return render_template("user.html", **context)

@app.route('/followSubpage/', methods=['POST'])
def followSubpage():
  sid = request.args.get('sid')
  uid = session['uid']

  insert_follow_cmd = 'INSERT INTO follows(sid, uid) VALUES (:sid1, :uid1)';

  try:
    g.conn.execute(text(insert_follow_cmd), sid1 = sid, uid1 = uid);
  except exc.IntegrityError as e:
    print "already followed"

  return redirect(request.referrer)

@app.route('/unfollowSubpage/', methods=['POST'])
def unfollowSubpage():
  sid = request.args.get('sid')
  uid = session['uid']

  delete_follow_cmd = 'DELETE FROM follows WHERE sid=:sid and uid=:uid';
  g.conn.execute(text(delete_follow_cmd), sid=sid, uid=uid);

  return redirect(request.referrer)

# logic to add new user to a database
@app.route('/addpost/', methods=['POST'])
def addpost():
  uid = session['uid']
  sid = request.args.get('sid')
  title = request.form['title']
  body = request.form['body']
  body = body.replace("\'", "\'\'")

  cmd = 'INSERT INTO post(uid, sid, title, body, date_posted) VALUES (:uid, :sid, :title, :body, now())';
  g.conn.execute(text(cmd), uid=uid, sid=sid, title=title, body=body);

  return redirect(request.referrer)

@app.route('/delpost/', methods=['POST'])
def delpost():
  pid = request.args.get("pid")

  cmd = 'DELETE FROM post WHERE pid = :pid;';
  g.conn.execute(text(cmd), pid=pid)

  return redirect(request.referrer)

# render a page to create a new subpage
@app.route('/newsubpage', methods=['GET'])
def newsubpage():
  return render_template("newsubpage.html")

# logic to add new user to a database
@app.route('/addsubpage', methods=['POST'])
def addsubpage():
  sp_name = request.form['sp_name']
  description = request.form['description']

  cmd = 'INSERT INTO subpages(sp_name, description) VALUES (:sp_name, :description)';
  g.conn.execute(text(cmd), sp_name=sp_name, description=description);

  get_new_sid = 'select sid from subpages where sp_name=:sp_name';
  cursor = g.conn.execute(text(get_new_sid), sp_name=sp_name);
  result = cursor.first()
  sid = result['sid']

  try:
    cursor = g.conn.execute(text(get_new_sid));
  except exc.IntegrityError as e:
    print "already existing name"
    return redirect(request.referrer)
  
  result = cursor.first()
  sid = result['sid']
  return redirect('/subpage/?sid={}'.format(sid))

@app.route('/delsubpage/', methods=['GET'])
def delsubpage():
  pass
  # TODO

# allow the current user to vote on a post
@app.route('/votepost/', methods=['POST'])
def votePost():
  pid = request.args.get('pid')
  uid = session['uid']

  insert_vote_cmd = 'INSERT INTO vote(uid_vote, pid) VALUES (:uid1, :pid1)';

  try:
    g.conn.execute(text(insert_vote_cmd), uid1 = uid, pid1 = pid);
  except exc.IntegrityError as e:
    print "already voted"

  return redirect(request.referrer)

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
