#Ruqqus installation wizard
import pip
import os
from os import environ
import sys
import venv
import secrets

print("")
print("")
print('   /\\')
print(' _/__\\_')
print(' ╭───────╮')
print('╭┤  ╹ ╹  ├╮')
print(' ╰─┬───┬─╯')
print("")
print("")
print("Welcome. I am the Ruqqus Installation and Setup Wizard.")
print("I will guide you through the process of setting up your own Ruqqus server.")
print("")

if float(sys.version[0:3])<3.6:
    print("First, install Python 3.5 or higher.")
    print("If it's already installed, rerun the wizard using the command `python3` instead of `python`.")
    quit(0)

#navigate to folder above ruqqus repo
path=os.path.realpath('.')
if path.endswith("scripts"):
    path=os.path.realpath(path+"/..")
if path.endswith("ruqqus"):
    path=os.path.realpath(path+"/..")

files=os.listdir(path)

first="env.sh" not in files

if not first:
    os.system(f"source {path}/env.sh")

if "venv" not in files:


    print("")
    print("")
    print('   /\\')
    print(' _/__\\_')
    print(' ╭───────╮')
    print('╭┤  ╹ ╹  ├╮')
    print(' ╰─┬───┬─╯')
    print("")
    print("")
    print("First, I will create a virtual Python environment for Ruqqus to run in.")
    print("This pocket universe will contain everything Ruqqus needs.")
    print("This will be created at:")
    print(f"{path}/venv")
    print("")
    input("Press enter to continue.")

    os.system(f"python3 -m venv {path}/venv")

    print("Now, run the following command, and then rerun the wizard.")
    print("")
    print(f"source {path}/venv/bin/activate")
    print("")
    quit(0)




print("")
print("")
print('   /\\')
print(' _/__\\_')
print(' ╭───────╮')
print('╭┤  ╹ ╹  ├╮')
print(' ╰─┬───┬─╯')
print("")
print("")
print("Now, I'm going to update the environment with everything Ruqqus needs.")
print("This may take a moment, especially if it's the first time.")
print("")
input("Press enter to continue.")

os.system("pip install --upgrade pip")
os.system(f"pip install -r {path}/ruqqus/requirements.txt")

sys.path.append(f"{path}/ruqqus")
from werkzeug.security import generate_password_hash
import sqlalchemy


print("")
print("")
print('   /\\')
print(' _/__\\_')
print(' ╭───────╮')
print('╭┤  ╹ ╹  ├╮')
print(' ╰─┬───┬─╯')
print("")
print("")


print("Next, I need some information to cast my setup spells.")
if "env.sh" in files:
    with open(f"{path}/env.sh", "r+") as f:
        for line in f:
            line=line.strip()
            if not line:
                continue
            args=line.split("=")
            val=args[1] if len(args)>1 else ""
            key=args[0].split("export ")[1]
            os.environ[key]=val

    print("This information is required,")
    print("but you can press enter to skip items and leave them at their current setting")
else:
    print("This information is required.")

envs={}

if first:
    print("What is the name of your site? (This will also be the username of the system admin account)")
else:
    print("What is the name of your site?")
envs["SITE_NAME"]=input().lower() or environ.get("SITE_NAME")

if first:
    print(f"Enter a password for the {envs['SITE_NAME']} system account:")
    password_hash=generate_password_hash(input())

print("What is the domain that your site will run under?")
envs["SERVER_NAME"]=input().lower() or environ.get("SERVER_NAME") or "localhost:5000"

print("Postgres database url (postgres://username:password@host:port/dbname)")
envs["DATABASE_URL"]=input() or environ.get("DATABASE_URL")

print("")
print("")
print('   /\\')
print(' _/__\\_')
print(' ╭───────╮')
print('╭┤  ╹ ╹  ├╮')
print(' ╰─┬───┬─╯')
print("")
print("")
print("Thank you for that.")
print("There's some more information I'd like.")
print("These are optional, but allow for more features and better performance")
print("if you can provide them.")
print("To skip any item, or to leave it at its current setting,just press enter.")

print("Master Secret (If you don't have one already, I'll generate one for you.)")
envs["MASTER_KEY"]=input() or environ.get("MASTER_KEY", secrets.token_urlsafe(1024))

print("Redis url (redis://host)")
envs["REDIS_URL"]=input() or environ.get("REDIS_URL", "") or ""
envs["CACHE_TYPE"]="redis" if envs["REDIS_URL"] else "filesystem"

print("")
print("")
print('   /\\')
print(' _/__\\_')
print(' ╭───────╮')
print('╭┤  ╹ ╹  ├╮')
print(' ╰─┬───┬─╯')
print("")
print("")
print("Next, I'll ask you about some third-party services that I can integrate with.")
print("")

if first:
    print("Are you using Giphy for gif insertion? (y/n)")
else:
    print("Change Giphy settings? (y/n)")
if input().startswith('y'):
    print("Giphy Key:")
    envs["GIPHY_KEY"]=input() or environ.get("GIPHY_KEY")
else:
    envs["GIPHY_KEY"]=environ.get("GIPHY_KEY","")

if first:
    print("Are you using AWS S3 to host images? (y/n)")
else:
    print("Change AWS S3 settings? (y/n)")

if input().startswith('y'):

    print("S3 Bucket Name")
    print(f"This should be a subdomain of your main site domain, for example, i.{envs['SERVER_NAME']}")
    envs["S3_BUCKET_NAME"]=input() or environ.get("S3_BUCKET_NAME","")

    print("AWS Access Key ID:")
    envs["AWS_ACCESS_KEY_ID"]=input() or environ.get("AWS_ACCESS_KEY_ID","")

    print("AWS Secret Access Key:")
    envs["AWS_SECRET_ACCESS_KEY"]=input() or environ.get("AWS_SECRET_ACCESS_KEY","")

else:
    envs["S3_BUCKET_NAME"]=environ.get("S3_BUCKET_NAME","")
    envs["AWS_ACCESS_KEY_ID"]=environ.get("AWS_ACCESS_KEY_ID","")
    envs["AWS_SECRET_ACCESS_KEY"]=environ.get("AWS_SECRET_ACCESS_KEY","")

if first:
    print("Are you using CloudFlare? (y/n)")
else:
    print("Change CloudFlare settings? (y/n)")
if input().startswith('y'):

    print("Cloudflare API Key:")
    envs["CLOUDFLARE_KEY"]=input() or environ.get("CLOUDFLARE_KEY","")

    print("Cloudflare Zone:")
    envs["CLOUDFLARE_ZONE"]=input() or environ.get("CLOUDFLARE_ZONE","")

else:
    envs["CLOUDFLARE_KEY"]=environ.get("CLOUDFLARE_KEY","")
    envs["CLOUDFLARE_ZONE"]=environ.get("CLOUDFLARE_ZONE","")

if first:
    print("Are you using HCaptcha to block bot signups? (y/n)")
else:
    print("Change HCaptcha settings? (y/n)")

if input().startswith('y'):
    print("HCaptcha Site Key")
    envs["HCAPTCHA_SITEKEY"]=input() or environ.get("HCAPTCHA_SITEKEY","")

    print("HCaptcha Secret")
    envs["HCAPTCHA_SECRET"]=input() or environ.get("HCAPTCHA_SECRET","")
else:
    envs["HCAPTCHA_SITEKEY"]=environ.get("HCAPTCHA_SITEKEY","")
    envs["HCAPTCHA_SECRET"]=environ.get("HCAPTCHA_SECRET","")

if first:
    print("Are you using MailGun as an email provider? (y/n)")
else:
    print("Change MailGun settings? (y/n)")
if input().startswith('y'):
    print("Your email:")
    envs["admin_email"]=input() or environ.get("admin_email","")

    print("Mailgun Key:")
    envs["MAILGUN_KEY"]=input() or environ.get("MAILGUN_KEY","")

if first:
    print("Are you using PayPal for premium payments? (y/n)")
else:
    print("Change PayPal settings? (y/n)")
if input().startswith('y'):
    print("Paypal Client ID:")
    envs["PAYPAL_CLIENT_ID"]=input() or environ.get("PAYPAL_CLIENT_ID","")

    print("PayPal Client Secret:")
    envs["PAYPAL_CLIENT_SECRET"]=input() or environ.get("PAYPAL_CLIENT_SECRET","")

    print("PayPal Webhook ID:")
    envs["PAYPAL_WEBHOOK_ID"]=input() or environ.get("PAYPAL_WEBHOOK_ID","")
else:
    envs["PAYPAL_CLIENT_ID"]=environ.get("PAYPAL_CLIENT_ID","")
    envs["PAYPAL_CLIENT_SECRET"]=environ.get("PAYPAL_CLIENT_SECRET","")
    envs["PAYPAL_WEBHOOK_ID"]=environ.get("PAYPAL_WEBHOOK_ID","")


envs["PYTHONPATH"]=f"$PYTHONPATH:{path}/ruqqus"


keys=sorted([x for x in envs.keys()])

#make the envs.sh
with open(f"{path}/env.sh", "w+") as f:
    f.write("\n".join([f"export {x}={envs[x]}" for x in keys]))

#load envs for import
for x in envs:
    os.environ[x]=envs.get(x) or ""


###db setup sql
if first or envs["DATABASE_URL"]!=environ.get("DATABASE_URL"):
    print("")
    print("")
    print('   /\\')
    print(' _/__\\_')
    print(' ╭───────╮')
    print('╭┤  ╹ ╹  ├╮')
    print(' ╰─┬───┬─╯')
    print("")
    print("")
    if first:
        print("Since this is the first time setting up and the database is brand new,")
    else:
        print("Since you changed the postgres database settings,")
    print("I need to connect to it and set that up too.")
    print("This may take some time.")
    print("")
    input("Press enter to set up database.")

    engine = sqlalchemy.create_engine(envs["DATABASE_URL"])
    try:
        with engine.begin() as conn:
            with open(f"{path}/ruqqus/schema.sql", "r+") as file:
                escaped_sql = sqlalchemy.text(file.read())
                conn.execute(escaped_sql)
    except Exception as e:
        print("Tables already exist, skipping seed data")
    else:
        with engine.begin() as conn:
            with open(f"{path}/ruqqus/seed-db.sql", "r+") as file:
                escaped_sql = sqlalchemy.text(file.read())
                conn.execute(escaped_sql)


    os.system(f"source {path}/env.sh")
    from ruqqus.__main__ import *
    from ruqqus.classes import *

    db=db_session()
    sys_account = User(
        id=1,
        username=envs["SITE_NAME"],
        original_username = envs["SITE_NAME"],
        passhash=password_hash,
        email=envs.get("admin_email",""),
        created_utc=int(time.time()),
        tos_agreed_utc=int(time.time()),
        )

    try:
        db.add(sys_account)
        db.commit()
    except:
        print(f"@{envs['SITE_NAME']} already exists")

    general_guild=Board(
        id=1,
        name="general",
        description="All topics. Content posted here may be yanked to other guilds.",
        description_html="<p>All topics. Content posted here may be yanked to other guilds.</p>",
        over_18=False,
        created_utc=int(time.time()),
        creator_id=1
        )

    try:
        db.add(general_guild)
        db.commit()
    except:
        "+general already exists"

start_script=f"""
killall gunicorn
killall Python
cd {path}/ruqqus
git pull
cd {path}
#sudo cp {path}/ruqqus/nginx.txt /etc/nginx/sites-available/ruqqus.com.conf
#sudo nginx -s reload
. {path}/venv/bin/activate
. {path}/env.sh
cd {path}/ruqqus
pip3 install -r requirements.txt
export PYTHONPATH=$PYTHONPATH:~/ruqqus
cd {path}
echo "starting background worker"
python {path}/ruqqus/scripts/recomputes.py
#echo "starting chat worker"
#gunicorn ruqqus.__main__:app -k eventlet  -w 1 --worker-connections 1000 --max-requests 100000 --preload --bind 0.0.0.0:5001 -D
echo "starting regular workers"
newrelic-admin run-program gunicorn ruqqus.__main__:app -k gevent -w 2 --worker-connections 5 --max-requests 10000 --max-requests-jitter 500 --preload --bind 0.0.0.0:5000
"""

with open(f"{path}/go.sh", "w+") as f:
    f.write(start_script)


print("")
print("")
print('   /\\')
print(' _/__\\_')
print(' ╭───────╮')
print('╭┤  ╹ ╹  ├╮')
print(' ╰─┬───┬─╯')
print("")
print("")
print("Ruqqus is set up! To start Ruqqus navigate to the folder above the repository and run `source go.sh`")
