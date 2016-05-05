import sys
sys.path.insert(0, '/var/www/moca')

activate_this = '/var/www/moca/venv/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))

from app import app as application
