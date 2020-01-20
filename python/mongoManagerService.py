
# This file is part of DITAS Marketplace Repository Scaling.
# 
# DITAS Marketplace Repository Scaling is free software: you can redistribute it 
# and/or modify it under the terms of the GNU General Public License as 
# published by the Free Software Foundation, either version 3 of the License, 
# or (at your option) any later version.
# 
# DITAS Marketplace Repository Scaling is distributed in the hope that it will be 
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with DITAS Marketplace Repository Scaling.  
# If not, see <https://www.gnu.org/licenses/>.
# 
# DITAS Marketplace Repository Scaling is being developed for the
# DITAS Project: https://www.ditas-project.eu/

from flask import Flask
from flask_cors import CORS
import dockerHandler, mongoHandler, mondoBacman, logsHandler

def create_app():
	app = Flask(__name__)
	
	#Setup CORS policy
	cors = CORS(app, resources={
		r"/mongo/*": {"origins": "*"},
		r"/docker/*": {"origins": "*"},
		r"/manager/*": {"origins": "*"},
		r"/logs/*": {"origins": "*"}
	})

	app.register_blueprint(dockerHandler.create_blueprint())
	app.register_blueprint(mongoHandler.create_blueprint())
	app.register_blueprint(mondoBacman.create_blueprint())
	app.register_blueprint(logsHandler.create_blueprint())
	
	return app