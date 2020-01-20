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
from pymongo import MongoClient
import docker, json, gzip, io, requests, time, dockerHandler, config, traceback

default_ports = {'config':'27018','shard':'27020','app':'27017'}
default_host_ports = {'config':'50118','shard':'50120','app':'50117'}

#Compresses the content using gzip compression
def gzipencode(content,responseType,acceptEncoding):
    if 'gzip' in [enco.strip() for enco in acceptEncoding.split(',')]:
        compressed_data = gzip.compress(bytes(content,'utf-8'))
        resp = Response(compressed_data,  mimetype=responseType)
        resp.headers['Content-Encoding'] = 'gzip'
        return resp
    else:
        return Response(content,  mimetype=responseType)

# Gets all containers participating in a cluster
def getClusterContainers(mongo_server,mongo_port,baseUrl,username):
    resContainers = []
    try:
        mes = requests.post(url=config.host+"/mongo/getClusterMap",json={'mongo_server': mongo_server,'mongo_port': mongo_port}).json()
        replicas = []
        for key in mes.get('success',{}):
            if key == 'config':
                replicas.append(mes['success'][key].split('/')[0])
            else:
                replicas.append(key)
        if len(replicas) > 0:
            # Connect to docker
            c = docker.DockerClient(base_url=baseUrl, version='auto')
            conts = c.containers.list(filters={'label': 'user=' + username}, all=True)
            for container in conts:
                contRS = container.image.labels.get('rs', '')
                contPort = container.labels.get('port', '')
                contHost = container.labels.get('host', '')
                if ('rs'+str(contRS) in replicas) or (int(contPort) == int(mongo_port) and contHost == mongo_server):
                    resContainers.append(container)
    except Exception as ex:
        print(ex)
    return resContainers


#Creates the flask application
def create_blueprint():
    # Define the application.
    mondo_backman = Blueprint('mondo_backman', __name__)

    @mondo_backman.route('/manager/destroyCluster', methods=['POST'])
    def destroyCluster(conf = None):
        try:
            if conf is None:
                conf = request.json
            if conf is None:
                return gzipencode(json.dumps({'error': 'No Configuration Provided.'}), 'application/json',
                                  request.headers.get('Accept-Encoding'))

            mongoServer = conf.get('mongo_server','localhost')
            mongoPort = conf.get('mongo_port','27017')
            baseUrl = conf.get('base_url', 'unix://var/run/docker.sock')
            username = conf.get('username', None)

            containers = getClusterContainers(mongoServer,mongoPort,baseUrl,username)
            mes = []
            for cont in containers:
                print({'label':cont.labels.get('type', ''),'host':cont.labels.get('host', ''),'port':cont.labels.get('port', '')})
                if cont.labels.get('type', '') == 'shard':
                    print('Removing it...')
                    mes.append(requests.post(url=config.host+"/manager/removeServer",json={'mongo_server': mongoServer, 'mongo_port': mongoPort,'username': username, 'base_url': baseUrl,'id': cont.short_id}).json())
                    print(mes[-1])
                    time.sleep(5)
            return gzipencode(json.dumps({'success':mes}), 'application/json', request.headers.get('Accept-Encoding'))
        except Exception as ex:
            print(ex)
            return gzipencode(json.dumps({'error': str(ex)}), 'application/json',
                              request.headers.get('Accept-Encoding'))

    @mondo_backman.route('/manager/getClusterMaps/<username>', methods=['GET'])
    def getClusterMaps(username):
        try:
            configClient = MongoClient(host=config.mongoHost,port=int(config.mongoPort),username=config.username,password=config.password,authSource=config.database)
            configDB = configClient[config.database]['replicaSetLogs']
            rsResMongo = list(configDB.find({'_id':username}))[0]
            cleanMaps = []
            if 'accessPoints' in rsResMongo:
                for ap in rsResMongo['accessPoints']:
                    mes = requests.post(url = config.host+"/mongo/getClusterMap", json = {'mongo_server':rsResMongo['accessPoints'][ap]['host'],'mongo_port':rsResMongo['accessPoints'][ap]['port']}).json()
                    map = mes['success']
                    cleanMap = {}
                    for key in map:
                        if not ':' in key:
                            cleanMap[key] = map[key]
                    cleanMap['access_point']=str(rsResMongo['accessPoints'][ap]['host'])+':'+rsResMongo['accessPoints'][ap]['port']
                    cleanMaps.append(cleanMap)
            return gzipencode(json.dumps(cleanMaps),'application/json',request.headers.get('Accept-Encoding'))
        except Exception as ex:
            track = traceback.format_exc()
            print(track)
            return gzipencode(json.dumps({'error':str(ex)}),'application/json',request.headers.get('Accept-Encoding'))
    
    @mondo_backman.route('/manager/getClusterMap', methods=['POST'])
    def getClusterMap(conf = None):
        try:
            if conf is None:
                conf = request.json
            if conf is None:
                return gzipencode(json.dumps({'error':'No Configuration Provided.'}),'application/json',request.headers.get('Accept-Encoding'))
            
            # mongoServer = conf.get('mongo_server','localhost')
            # mongoPort = conf.get('mongo_port','27017')

            mes = requests.post(url = config.host+"/mongo/getClusterMap", json = conf).json()
            map = mes['success']
            cleanMap = {}
            for key in map:
                if not ':' in key:
                    cleanMap[key] = map[key]
            return gzipencode(json.dumps(cleanMap),'application/json',request.headers.get('Accept-Encoding'))
        except Exception as ex:
            print(ex)
            return gzipencode(json.dumps({'error':str(ex)}),'application/json',request.headers.get('Accept-Encoding'))
            
    @mondo_backman.route('/manager/runCluster', methods=['POST'])
    def runCluster(conf = None):
        try:
            if conf is None:
                conf = request.json
            if conf is None:
                return gzipencode(json.dumps({'error':'No Configuration Provided.'}),'application/json',request.headers.get('Accept-Encoding'))
            
            baseUrl = conf.get('base_url','unix://var/run/docker.sock')
            username = conf.get('username',None)
            appServers = conf.get('app',[])
            configServers = conf.get('config',[])
            shardServers = conf.get('shard',[])
            defaultHost = conf.get('default_host','localhost')
            res=[]
            
            # Check if at least one of each type is present
            print('Checking cluster configuration...')
            if len(appServers) == 0 or len(configServers) == 0 or len(shardServers) == 0:
                return gzipencode(json.dumps({'error':'You need to provide at least one server of each type (app, config and shard).'}),'application/json',request.headers.get('Accept-Encoding'))
            print('Check passed!')
            
            for srv in appServers:
                srv['type'] = 'app'
                if not 'host' in srv:    srv['host'] = defaultHost
                mes = requests.post(url = config.host+"/manager/addServer", json = {
                    'base_url':baseUrl,
                    'username':username,
                    'mongo_server':appServers[0]['host'],
                    'mongo_port':appServers[0]['port'],
                    'rs':srv['rs'],
                    'type':srv['type'],
                    'host':srv['host'],
                    'port':srv['port']
                }).json()
                res.append({'appSrv':srv,'message':str(mes)})
            for srv in configServers:
                srv['type'] = 'config'
                if not 'host' in srv:    srv['host'] = defaultHost
                mes = requests.post(url = config.host+"/manager/addServer", json = {
                    'base_url':baseUrl,
                    'username':username,
                    'mongo_server':appServers[0]['host'],
                    'mongo_port':appServers[0]['port'],
                    'rs':srv['rs'],
                    'type':srv['type'],
                    'host':srv['host'],
                    'port':srv['port']
                }).json()
                res.append({'confSrv':srv,'message':str(mes)})
            for srv in shardServers:
                srv['type'] = 'shard'
                if not 'host' in srv:    srv['host'] = defaultHost
                mes = requests.post(url = config.host+"/manager/addServer", json = {
                    'base_url':baseUrl,
                    'username':username,
                    'mongo_server':appServers[0]['host'],
                    'mongo_port':appServers[0]['port'],
                    'rs':srv['rs'],
                    'type':srv['type'],
                    'host':srv['host'],
                    'port':srv['port']
                }).json()
                res.append({'shardSrv':srv,'message':str(mes)})
            
            # Return access point
            accessPoints = []
            for srv in appServers:
                accessPoints.append(srv['host']+":"+srv['port'])

            res = {'access_points':accessPoints,'debug':res}
            return gzipencode(json.dumps(res),'application/json',request.headers.get('Accept-Encoding'))
        except Exception as ex:
            track = traceback.format_exc()
            print(track)
            return gzipencode(json.dumps({'error':str(ex)}),'application/json',request.headers.get('Accept-Encoding'))
    
    #Adds a new server to the cluster
    # noinspection PyBroadException
    @mondo_backman.route('/manager/addServer', methods=['POST'])
    def addServer(conf = None):
        try:
            if conf is None:
                conf = request.json
            if conf is None:
                return gzipencode(json.dumps({'error':'No Configuration Provided.'}),'application/json',request.headers.get('Accept-Encoding'))
               
            print({'Adding':str(conf)})
            print('----------------------------')
            
            baseUrl = conf.get('base_url','unix://var/run/docker.sock')
            username = conf.get('username',None)
            mongoServer = conf.get('mongo_server','localhost')
            mongoPort = conf.get('mongo_port','27017')
            replicaID = conf.get('rs','0')
            serverType = conf.get('type','shard')
            hostIP = conf.get('host','localhost')
            hostPort = conf.get('port',default_host_ports[serverType])
            cID = conf.get('id',None)
            res=[]
            
            try:
                mes = requests.post(url = config.host+"/mongo/getClusterMap", json = conf, timeout=1.5).json()
                map = json.dumps(mes['success'])
                if (hostIP + ':' + hostPort) in map:
                    return gzipencode(json.dumps({'success':'Already added'}),'application/json',request.headers.get('Accept-Encoding'))
            except:
                None
            
            #Connect to docker
            c = docker.DockerClient(base_url=baseUrl,version='auto')
            
            #If a container ID was provided just start this container and update RS.
            if cID is not None:
                container = c.containers.get(cID)
                container.start()
                contType = container.labels.get('type','')
                contRS = container.image.labels.get('rs','')
                contPort = container.labels.get('port','')
                contHost = container.labels.get('host','')
                if contType != 'app':
                    rsConfig = {
                        'mongo_server':contHost,
                        'mongo_port':int(contPort),
                        'rs':'rs'+str(contRS),
                        'machines':[{'host':contHost+':'+str(contPort)}],
                        'username':username,
                        'configServer':(contType=='config')
                    }
                    mes = requests.post(url = config.host+"/mongo/addToReplicaSet", json = rsConfig).json()
                    res.append({'rsConf':rsConfig,'message':str(mes)})
                    if contType == 'shard':
                        mes = requests.post(url = config.host+"/mongo/addShard", json = {'mongo_server':mongoServer,'mongo_port':mongoPort,'shard':'rs'+contRS+'/'+contHost+':'+contPort}).json()
                        res.append({'addShard':rsConfig,'message':str(mes)})
                else:
                    userLogs = {'_id':username}
                    configClient = MongoClient(host=config.mongoHost,port=int(config.mongoPort),username=config.username,password=config.password,authSource=config.database)
                    configDB = configClient[config.database]['replicaSetLogs']
                    try:
                        userLogs = list(configDB.find({'_id':username}))[0]
                    except:
                        None
                    if 'accessPoints' in userLogs:
                        userLogs['accessPoints'][contHost+':'+contPort] = {'host':contHost,'port':contPort}
                    else:
                        userLogs['accessPoints'] = {contHost+':'+contPort:{'host':contHost,'port':contPort}}
                    configDB.update({'_id':username},userLogs,upsert=True)
                c.close()
                return gzipencode(json.dumps({'success':cID}),'application/json',request.headers.get('Accept-Encoding'))
            
            # Check if images created and return error if not
            srv = {'rs':str(replicaID),'type':str(serverType),'port':str(hostPort),'host':str(hostIP)}
            print('Checking required images for '+json.dumps(srv))
            imageTagsToCheck = {}
            containerIndex = {}
            rsConfig = {}
            imageTagsToCheck['rs'+srv['rs'].lower()+'_'+srv['type']+'_server']=0
            containerIndex[srv['rs']+'_'+srv['port']+'_'+srv['type']] = {'status':None,'srv':srv}
            if serverType != 'app':
                rsConfig = {
                    'mongo_server':srv['host'],
                    'mongo_port':int(srv['port']),
                    'rs':'rs'+srv['rs'],
                    'machines':[{'host':srv['host']+':'+str(srv['port'])}],
                    'username':username,
                    'configServer':(serverType=='config')
                }
            for tag in imageTagsToCheck:
                try:
                    img = c.images.get(tag)
                    if img is not None:
                        imageTagsToCheck[tag]+=1
                except Exception as exexe:
                    return gzipencode(json.dumps({'error':str(exexe)}),'application/json',request.headers.get('Accept-Encoding'))
            print('Check passed!')
            
            # Check already available containers
            print('Checking available containers...')
            conts = c.containers.list(filters={'label':'user='+username},all=True)
            appContainers = []
            configContainers = []
            shardContainers = []
            for container in conts:
                contType = container.labels.get('type','')
                contRS = container.image.labels.get('rs','')
                contPort = container.labels.get('port','')
                if contType == 'app' and (contRS + '_' + contPort + '_' + contType) in containerIndex:
                    appContainers.append(container)
                elif contType == 'config' and (contRS + '_' + contPort + '_' + contType) in containerIndex:
                    configContainers.append(container)
                elif contType == 'shard' and (contRS + '_' + contPort + '_' + contType) in containerIndex:
                    shardContainers.append(container)
            
            # Start stopped containers matching the cluster    
            print('Using available containers...')
            for container in configContainers:
                contType = container.labels.get('type','')
                contRS = container.image.labels.get('rs','')
                contPort = container.labels.get('port','')
                if container.status != "running":
                    container.start()
                    containerIndex[contRS+'_'+contPort+'_'+contType]['status'] = 'started'
                else:
                    containerIndex[contRS+'_'+contPort+'_'+contType]['status'] = 'running'
            for container in shardContainers:
                contType = container.labels.get('type','')
                contRS = container.image.labels.get('rs','')
                contPort = container.labels.get('port','')
                if container.status != "running":
                    container.start()
                    containerIndex[contRS+'_'+contPort+'_'+contType]['status'] = 'started'
                else:
                    containerIndex[contRS+'_'+contPort+'_'+contType]['status'] = 'running'
            for container in appContainers:
                contType = container.labels.get('type','')
                contRS = container.image.labels.get('rs','')
                contPort = container.labels.get('port','')
                if container.status != "running":
                    container.start()
                    containerIndex[contRS+'_'+contPort+'_'+contType]['status'] = 'started'
                else:
                    container.stop()
                    container.start()
                    containerIndex[contRS+'_'+contPort+'_'+contType]['status'] = 'restarted'
            
            # Create missing containers and start them
            print('Creating missing containers...')
            for srvIndex in containerIndex:
                if containerIndex[srvIndex]['status'] is None:
                    srv = containerIndex[srvIndex]['srv']
                    containerConf = {'username':username,'base_url':baseUrl,'type':srv['type'],'hostport':srv['port'],'host':srv['host'],'rs':srv['rs']}
                    r = requests.post(config.host+'/docker/runContainer', json=containerConf)
                    if r.status_code == 200:
                        result = r.json()
                        if 'started' in result:
                            containerIndex[srvIndex]['status'] = 'created'
                    if containerIndex[srvIndex]['status'] != 'created':
                        raise Exception('Could not start container with index: '+srvIndex)
            #print(json.dumps(containerIndex))
            
            time.sleep(1)
            
            # Config cluster using mongoDB Handlers
            if serverType != 'app':
                mes = requests.post(url = config.host+"/mongo/addToReplicaSet", json = rsConfig).json()
                res.append({'rsConf':rsConfig,'message':str(mes)})
            else:
                userLogs = {'_id':username}
                configClient = MongoClient(host=config.mongoHost,port=int(config.mongoPort),username=config.username,password=config.password,authSource=config.database)
                configDB = configClient[config.database]['replicaSetLogs']
                try:
                    userLogs = list(configDB.find({'_id':username}))[0]
                except: None
                if 'accessPoints' in userLogs:
                    userLogs['accessPoints'][hostIP+':'+hostPort] = {'host':hostIP,'port':hostPort}
                else:
                    userLogs['accessPoints'] = {hostIP+':'+hostPort:{'host':hostIP,'port':hostPort}}
                configDB.update({'_id':username},userLogs,upsert=True)
            if serverType == 'shard':
                mes = requests.post(url = config.host+"/mongo/addShard", json = {'mongo_server':mongoServer,'mongo_port':mongoPort,'shard':'rs'+replicaID+'/'+hostIP+':'+hostPort}).json()
                res.append({'addShard':rsConfig,'message':str(mes)})

            res = {'success':True,'debug':res}
            print({'res':res})
            print('----------------------------')
            c.close()
            return gzipencode(json.dumps(res),'application/json',request.headers.get('Accept-Encoding'))
        except Exception as ex:
            track = traceback.format_exc()
            print(track)
            c.close()
            return gzipencode(json.dumps({'error':str(ex)}),'application/json',request.headers.get('Accept-Encoding'))
    
    # Removes the server from the cluster. If the server is the last shard it destroys the cluster.
    @mondo_backman.route('/manager/removeServer', methods=['POST'])
    def removeServer(conf = None):
        try:
            if conf is None:
                conf = request.json
            if conf is None:
                return gzipencode(json.dumps({'error':'No Configuration Provided.'}),'application/json',request.headers.get('Accept-Encoding'))
            
            baseUrl = conf.get('base_url','unix://var/run/docker.sock')
            username = conf.get('username',None)
            mongoServer = conf.get('mongo_server', 'localhost')
            mongoPort = conf.get('mongo_port', '27017')
            cID = conf.get('id',None)
            res=[]
            
            #Connect to docker
            c = docker.DockerClient(base_url=baseUrl,version='auto')
            
            #If a container ID was provided just start this container and update RS.
            if cID is not None:
                container = c.containers.get(cID)
                contType = container.labels.get('type','')
                contRS = container.image.labels.get('rs','')
                contPort = container.labels.get('port','')
                contHost = container.labels.get('host','')
                
                userLogs = {'_id':username}
                configClient = MongoClient(host=config.mongoHost,port=int(config.mongoPort),username=config.username,password=config.password,authSource=config.database)
                configDB = configClient[config.database]['replicaSetLogs']
                try:
                    userLogs = list(configDB.find({'_id':username}))[0]
                except Exception as ex:
                    print({'rsDBRetrievalError':ex})
                
                if contType != 'app':
                    rsConfig = {
                        'mongo_server':contHost,
                        'mongo_port':int(contPort),
                        'rs':'rs'+str(contRS),
                        'machines':[{'host':contHost+':'+str(contPort)}],
                        'username':username,
                        'configServer':(contType=='config')
                    }
                    mes = requests.post(url = config.host+"/mongo/removeFromReplicaSet", json = rsConfig).json()
                    print({'removingFromRS':contHost+":"+contPort,'mes':mes})
                    if 'remove last member' in str(mes):
                        if contType == 'shard':
                            mes = requests.post(url = config.host+"/mongo/removeShard", json = {'mongo_server':mongoServer,'mongo_port':int(mongoPort),'shard':'rs'+contRS}).json()
                            print({'removingFromShards': contHost + ":" + contPort, 'mes': mes})
                            if 'remove last shard' in str(mes):
                                mes = []
                                conts = getClusterContainers(mongoServer, mongoPort, baseUrl, username)
                                appServers = []
                                others = []
                                for cont in conts:
                                    if cont.labels.get('type', '') == 'app':
                                        appServers.append(cont)
                                    elif int(cont.labels.get('port', '')) != int(contPort) or cont.labels.get('host', '') != contHost:
                                        others.append(cont)
                                for cont in others:
                                    print('Removing CONFs')
                                    mes.append(requests.post(url=config.host+"/manager/removeServer",
                                                        json={'mongo_server': mongoServer, 'mongo_port': mongoPort,
                                                              'username': username,'base_url':baseUrl,'id':cont.short_id}).json())
                                for cont in appServers:
                                    print('Removing APPs')
                                    mes.append(requests.post(url=config.host+"/manager/removeServer",
                                                        json={'mongo_server': mongoServer, 'mongo_port': mongoPort,
                                                              'username': username,'base_url':baseUrl,'id':cont.short_id}).json())
                            userLogs = list(configDB.find({'_id': username}))[0]
                            res.append({'removeShard':'rs'+contRS,'message':str(mes)})
                        if 'replicaSets' in userLogs:
                            if 'rs'+str(contRS) in userLogs['replicaSets']:
                                del userLogs['replicaSets']['rs'+str(contRS)]
                                configDB.update({'_id': username}, userLogs, upsert=True)
                    elif 'error' in str(mes):
                        print({'error':mes})
                    else:
                        if 'replicaSets' in userLogs:
                            if 'rs'+str(contRS) in userLogs['replicaSets']:
                                del userLogs['replicaSets']['rs'+str(contRS)]
                                configDB.update({'_id': username}, userLogs, upsert=True)
                    res.append({'rsConf':rsConfig,'message':str(mes)})
                else:
                    if 'accessPoints' in userLogs:
                        if contHost+ ':'+contPort in userLogs['accessPoints']:
                            del userLogs['accessPoints'][contHost+':'+contPort]
                            if len(userLogs['accessPoints']) == 0:
                                del userLogs['accessPoints']
                    configDB.update({'_id':username},userLogs,upsert=True)
                container.remove(force=True)
                c.close()
                return gzipencode(json.dumps({'success':cID}),'application/json',request.headers.get('Accept-Encoding'))
            else:
                c.close()
                raise Exception('Container ID not provided!')
        except Exception as ex:
            print(ex)
            c.close()
            return gzipencode(json.dumps({'error':str(ex)}),'application/json',request.headers.get('Accept-Encoding'))
            
    return mondo_backman