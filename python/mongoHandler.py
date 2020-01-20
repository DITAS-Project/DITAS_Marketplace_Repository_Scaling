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

import config
import gzip
import json
import time

from flask import Response, Blueprint, request
from pymongo import MongoClient


# Compresses the content using gzip compression
def gzipencode(content, responseType, acceptEncoding):
    if 'gzip' in [enco.strip() for enco in acceptEncoding.split(',')]:
        compressed_data = gzip.compress(bytes(content, 'utf-8'))
        resp = Response(compressed_data, mimetype=responseType)
        resp.headers['Content-Encoding'] = 'gzip'
        return resp
    else:
        return Response(content, mimetype=responseType)


# Creates the flask application
def create_blueprint():
    # Define the application.
    mongo_queries = Blueprint('mongo_queries', __name__)

    @mongo_queries.route('/mongo/pingServer', methods=['POST'])
    def pingServer(conf=None):
        try:
            if conf is None:
                conf = request.json

            mongoServer = conf.get('mongo_server', 'localhost')
            mongoPort = conf.get('mongo_port', '27017')

            c = MongoClient(mongoServer, int(mongoPort))

            res = []
            try:
                res.append(str(c.admin.command("ping", 1)))
            except Exception as exe:
                return gzipencode(json.dumps({'error': str(exe)}), 'application/json',
                                  request.headers.get('Accept-Encoding'))

            return gzipencode(json.dumps({'success': str(res)}), 'application/json',
                              request.headers.get('Accept-Encoding'))
        except Exception as ex:
            return gzipencode(json.dumps({'error': str(ex)}), 'application/json',
                              request.headers.get('Accept-Encoding'))

    @mongo_queries.route('/mongo/addShards', methods=['POST'])
    def addShards(conf=None):
        try:
            if conf is None:
                conf = request.json

            mongoServer = conf.get('mongo_server', 'localhost')
            mongoPort = conf.get('mongo_port', '27017')
            newShards = conf.get('shards', [])
            newShard = conf.get('shard', None)
            if newShard is not None:
                newShards.append(newShard)

            c = MongoClient(mongoServer, int(mongoPort))

            res = []
            for newShard in newShards:
                try:
                    res.append(c.admin.command("addShard", newShard))
                except Exception as exe:
                    res.append({'error': str(exe), 'shard': newShard})

            return gzipencode(json.dumps({'success': str(res)}), 'application/json',
                              request.headers.get('Accept-Encoding'))
        except Exception as ex:
            return gzipencode(json.dumps({'error': str(ex)}), 'application/json',
                              request.headers.get('Accept-Encoding'))

    @mongo_queries.route('/mongo/getRSConf', methods=['POST'])
    def getRSConf(conf=None):
        try:
            if conf is None:
                conf = request.json

            mongoServer = conf.get('mongo_server', 'localhost')
            mongoPort = conf.get('mongo_port', '27017')

            c = MongoClient(mongoServer, int(mongoPort))
            res = c.admin.command("replSetGetConfig", 1)
            return gzipencode(json.dumps({'success': str(res)}), 'application/json',
                              request.headers.get('Accept-Encoding'))
        except Exception as ex:
            return gzipencode(json.dumps({'error': str(ex)}), 'application/json',
                              request.headers.get('Accept-Encoding'))

    @mongo_queries.route('/mongo/ping', methods=['POST'])
    def ping(conf=None):
        try:
            if conf is None:
                conf = request.json

            mongoServer = conf.get('mongo_server', 'localhost')
            mongoPort = conf.get('mongo_port', '27017')

            c = MongoClient(mongoServer, int(mongoPort))
            res = c.config.command("ping", 1)
            return gzipencode(json.dumps({'success': str(res)}), 'application/json',
                              request.headers.get('Accept-Encoding'))
        except Exception as ex:
            return gzipencode(json.dumps({'error': str(ex)}), 'application/json',
                              request.headers.get('Accept-Encoding'))

    @mongo_queries.route('/mongo/getClusterMap', methods=['POST'])
    def getClusterMap(conf=None):
        try:
            if conf is None:
                conf = request.json

            mongoServer = conf.get('mongo_server', 'localhost')
            mongoPort = conf.get('mongo_port', '27017')

            c = MongoClient(mongoServer, int(mongoPort))
            res = c.admin.command("getShardMap", 1)
            return gzipencode(json.dumps({'success': res['map']}), 'application/json',
                              request.headers.get('Accept-Encoding'))
        except Exception as ex:
            return gzipencode(json.dumps({'error': str(ex)}), 'application/json',
                              request.headers.get('Accept-Encoding'))

    # Adds a new machine to the replicaSet
    @mongo_queries.route('/mongo/addToReplicaSet', methods=['POST'])
    def addToReplicaSet(conf=None):
        try:
            if conf is None:
                conf = request.json

            mongoServer = conf.get('mongo_server', 'localhost')
            mongoPort = conf.get('mongo_port', '27017')
            replicaID = conf.get('rs', 'rs0')
            confSrv = conf.get('configServer', False)
            username = conf.get('username', None)
            replicaMachines = conf.get('machines', [{'host': 'localhost:27020'}])

            c = MongoClient(mongoServer, int(mongoPort))
            configClient = MongoClient(host=config.mongoHost, port=int(config.mongoPort), username=config.username,
                                       password=config.password, authSource=config.database)
            configDB = configClient[config.database]['replicaSetLogs']

            rsConfig = {'_id': replicaID, 'members': []}
            replicaSets = {}
            rsResMongo = {'_id': username}

            memIndex = 0
            hostsToAdd = []
            hostsAdded = []
            for host in replicaMachines:
                hostsToAdd.append(host['host'])
            try:
                rsRes = c.admin.command("replSetGetConfig", 1)
                rsConfig['version'] = int(rsRes['config']['version']) + 1
                for mem in rsRes['config'].get('members',[]):
                    if mem['host'] not in hostsToAdd and mem['host'] not in hostsAdded:
                        rsConfig['members'].append({'_id': memIndex, 'host': mem['host']})
                        hostsAdded.append(mem['host'])
                        memIndex += 1
                for mem in replicaMachines:
                    if mem['host'] not in hostsAdded:
                        rsConfig['members'].append({'_id': memIndex, 'host': mem['host']})
                        hostsAdded.append(mem['host'])
                        memIndex += 1
                if rsRes['config'].get('configsvr', False):
                    rsConfig['configsvr'] = True
                res = c.admin.command("replSetReconfig", rsConfig, force=True)
            except Exception as exe:
                if str(exe).strip() == 'no replset config has been received':
                    try:
                        rsResMongo = list(configDB.find({'_id': username}))[0]
                        replicaSets = rsResMongo['replicaSets']
                        for mem in replicaSets[replicaID]['members']:
                            if mem['host'] not in hostsToAdd and mem['host'] not in hostsAdded:
                                rsConfig['members'].append({'_id': memIndex, 'host': mem['host']})
                                hostsAdded.append(mem['host'])
                                memIndex += 1
                        for mem in replicaMachines:
                            if mem['host'] not in hostsAdded:
                                rsConfig['members'].append({'_id': memIndex, 'host': mem['host']})
                                hostsAdded.append(mem['host'])
                                memIndex += 1
                        rsConfig['version'] = int(replicaSets[replicaID]['version']) + 1
                        #print({'rsConfigFromDB': rsConfig})
                        if confSrv:
                            rsConfig['configsvr'] = True
                        rsMaster = MongoClient(replicaSets[replicaID]['members'][0]['host'].split(':')[0],
                                               int(replicaSets[replicaID]['members'][0]['host'].split(':')[1]))
                        res = rsMaster.admin.command("replSetReconfig", rsConfig, force=True)
                        print('RS reconfigured')
                    except Exception as exexex:
                        print(str(exexex))
                        for mem in replicaMachines:
                            if mem['host'] not in hostsAdded:
                                rsConfig['members'].append({'_id': memIndex, 'host': mem['host']})
                                hostsAdded.append(mem['host'])
                                memIndex += 1
                        rsConfig['version'] = 1
                        print({'rsConfigNew': rsConfig})
                        res = c.admin.command("replSetInitiate", rsConfig)
                    if res.get('ok', 0) == 1:
                        res = "Replica set Initiated"
                    else:
                        res = str(res)
                else:
                    res = str(exe)
            replicaSets[replicaID] = rsConfig
            rsResMongo['replicaSets'] = replicaSets
            configDB.update({'_id': username}, rsResMongo, upsert=True)
            #print(res)

            return gzipencode(json.dumps({'success': str(res)}), 'application/json',
                              request.headers.get('Accept-Encoding'))
        except Exception as ex:
            print(ex)
            return gzipencode(json.dumps({'error': str(ex)}), 'application/json',
                              request.headers.get('Accept-Encoding'))

    # Needs to be tested ! {{checkpoint}}
    @mongo_queries.route('/mongo/removeFromReplicaSet', methods=['POST'])
    def removeFromReplicaSet(conf=None):
        try:
            if conf is None:
                conf = request.json

            mongoServer = conf.get('mongo_server', 'localhost')
            mongoPort = conf.get('mongo_port', '27017')
            replicaID = conf.get('rs', 'rs0')
            username = conf.get('username', None)
            replicaMachines = conf.get('machines', [{'host': 'localhost:27020'}])

            c = MongoClient(mongoServer, int(mongoPort))
            configClient = MongoClient(host=config.mongoHost, port=int(config.mongoPort), username=config.username,
                                       password=config.password, authSource=config.database)

            rsConfig = {'_id': replicaID, 'members': []}
            memIndex = 0
            hostsToRemove = []
            hostsAdded = []
            for host in replicaMachines:
                hostsToRemove.append(host['host'])

            configDB = configClient[config.database]['replicaSetLogs']
            rsResMongo = list(configDB.find({'_id': username}))[0]
            replicaSets = rsResMongo['replicaSets']
            try:
                res = c.admin.command("replSetGetConfig", 1)
                rsConfig['version'] = int(res['config']['version']) + 1
                for mem in res['config'].get('members',[]):
                    if mem['host'] not in hostsToRemove and mem['host'] not in hostsAdded:
                        rsConfig['members'].append({'_id': memIndex, 'host': mem['host']})
                        hostsAdded.append(mem['host'])
                        memIndex += 1
                if len(rsConfig['members']) > 0:
                    if res['config'].get('configsvr', False):
                        rsConfig['configsvr'] = True
                    c = MongoClient(rsConfig['members'][0]['host'].split(':')[0], int(rsConfig['members'][0]['host'].split(':')[1]))
                    #print({'old_conf': res['config'], 'new_conf': rsConfig})
                    res = c.admin.command("replSetReconfig", rsConfig, force=True)
                    replicaSets[replicaID] = rsConfig
                    rsResMongo['replicaSets'] = replicaSets
                    configDB.update({'_id': username}, rsResMongo, upsert=True)
                else:
                    raise Exception('Can\'t remove last member.')
            except Exception as exe:
                if str(exe).strip() == 'no replset config has been received':
                    res = "Replica set not Initiated"
                    if replicaID in replicaSets:
                        del replicaSets[replicaID]
                        rsResMongo['replicaSets'] = replicaSets
                        configDB.update({'_id': username}, rsResMongo, upsert=True)
                else:
                    raise exe
            #print(res)

            return gzipencode(json.dumps({'success': str(res)}), 'application/json',
                              request.headers.get('Accept-Encoding'))
        except Exception as ex:
            return gzipencode(json.dumps({'error': str(ex)}), 'application/json',
                              request.headers.get('Accept-Encoding'))

    @mongo_queries.route('/mongo/addShard', methods=['POST'])
    def addShard(conf=None):
        try:
            if conf is None:
                conf = request.json

            mongoServer = conf.get('mongo_server', 'localhost')
            mongoPort = conf.get('mongo_port', '27017')
            shard = conf.get('shard', None)

            c = MongoClient(mongoServer, int(mongoPort))
            res = str(c.admin.command("addShard", shard))

            return gzipencode(json.dumps({'success': str(res)}), 'application/json',
                              request.headers.get('Accept-Encoding'))
        except Exception as ex:
            return gzipencode(json.dumps({'error': str(ex)}), 'application/json',
                              request.headers.get('Accept-Encoding'))

    @mongo_queries.route('/mongo/removeShard', methods=['POST'])
    def removeShard(conf=None):
        try:
            if conf is None:
                conf = request.json

            mongoServer = conf.get('mongo_server', 'localhost')
            mongoPort = conf.get('mongo_port', '27017')
            shard = conf.get('shard', None)

            c = MongoClient(mongoServer, int(mongoPort))
            res = c.admin.command("removeShard", shard)
            while 'state' in res and res['state'] != 'completed':
                time.sleep(1)
                res = c.admin.command("removeShard", shard)

            return gzipencode(json.dumps({'success': str(res)}), 'application/json',
                              request.headers.get('Accept-Encoding'))
        except Exception as ex:
            return gzipencode(json.dumps({'error': str(ex)}), 'application/json',
                              request.headers.get('Accept-Encoding'))

    @mongo_queries.route('/mongo/configReplicaSet', methods=['POST'])
    def configReplicaSet(conf=None):
        try:
            if conf is None:
                conf = request.json

            mongoServer = conf.get('mongo_server', 'localhost')
            mongoPort = conf.get('mongo_port', '27017')
            replicaID = conf.get('rs', 'rs0')
            replicaMachines = conf.get('machines', [{'_id': 0, 'host': 'localhost:27020'}])

            c = MongoClient(mongoServer, int(mongoPort))

            rsConfig = {'_id': replicaID, 'members': replicaMachines}
            try:
                res = c.admin.command("replSetGetConfig", 1)
                rsConfig['version'] = int(res['config']['version']) + 1
                if res['config'].get('configsvr', False):
                    rsConfig['configsvr'] = True
                res = c.admin.command("replSetReconfig", rsConfig, force=True)
            except Exception as exe:
                if str(exe).strip() == 'no replset config has been received':
                    res = c.admin.command("replSetInitiate", rsConfig)
                    if res.get('ok', 0) == 1:
                        res = "Replica set Initiated"
                    else:
                        res = str(res)
                else:
                    res = str(exe)
            #print(res)

            return gzipencode(json.dumps({'success': str(res)}), 'application/json',
                              request.headers.get('Accept-Encoding'))
        except Exception as ex:
            return gzipencode(json.dumps({'error': str(ex)}), 'application/json',
                              request.headers.get('Accept-Encoding'))

    return mongo_queries
