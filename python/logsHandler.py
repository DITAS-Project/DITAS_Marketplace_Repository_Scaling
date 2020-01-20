# This Python file uses the following encoding: utf-8

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

from flask import Response, Blueprint, request

logs = {}

#Compresses the content using gzip compression
def gzipencode(content,responseType,acceptEncoding):
    try:
        if('gzip' in [enco.strip() for enco in acceptEncoding.split(',')]):
            compressed_data = gzip.compress(bytes(content,'utf-8'))
            resp = Response(compressed_data,  mimetype=responseType)
            resp.headers['Content-Encoding'] = 'gzip'
            return resp
    except: 
        None
    return Response(content,  mimetype=responseType)

#Creates the flask application
def create_blueprint():
    # Define the application.
    log_queries = Blueprint('log_queries', __name__)

    @log_queries.route('/log/enqueue/<queueName>', methods=['POST'])
    def enqueue(queueName):
		if queueName not in logs:
			logs[queueName]=[]
		data=request.json
		for point in data:
			logs[queueName].append(point)
		return gzipencode(json.dumps({'success':'queued'}),'application/json',request.headers.get('Accept-Encoding'))
		
	@log_queries.route('/log/consume/<queueName>', methods=['GET'])
    def consume(queueName):
		def generate():
			streamEnded = False
			if queueName not in logs:
				logs[queueName]=[]
			while len(logs[queueName]) > 0:
				yield logs[queueName].pop()
					
		return gzipencode(generate(),'application/json',request.headers.get('Accept-Encoding'))