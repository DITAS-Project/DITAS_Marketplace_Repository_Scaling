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
import docker, json, gzip, io, requests, time, traceback

default_ports = {'config':'27018','shard':'27020','app':'27017'}
default_host_ports = {'config':'50118','shard':'50120','app':'50117'}

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
    docker_queries = Blueprint('docker_queries', __name__)
    dockerfiles = {
        "config":"""
            FROM ubuntu_base:latest
            ARG replicaset
            ENV replicaset=$replicaset
            RUN su hduser -c 'mkdir -p ~/mongodb/db$replicaset'
            RUN su hduser -c 'mkdir -p ~/mongologs/db$replicaset'
            EXPOSE 27018
            ENTRYPOINT su hduser -c 'mongod --port 27018 --bind_ip_all --dbpath ~/mongodb/db$replicaset --configsvr --replSet rs$replicaset | tee ~/mongologs/db$replicaset/log'
        """,
        "shard":"""
            FROM ubuntu_base:latest
            ARG replicaset
            ENV replicaset=$replicaset
            RUN su hduser -c 'mkdir -p ~/mongodb/db$replicaset'
            RUN su hduser -c 'mkdir -p ~/mongologs/db$replicaset'
            EXPOSE 27020
            ENTRYPOINT su hduser -c 'mongod --port 27020 --bind_ip_all --dbpath ~/mongodb/db$replicaset --shardsvr --replSet rs$replicaset | tee ~/mongologs/db$replicaset/log'
        """,
        "app":"""
            FROM ubuntu_base:latest
            ARG replicaset
            ENV replicaset=$replicaset
            RUN su hduser -c 'mkdir -p ~/mongologs/db$replicaset'
            EXPOSE 27017
            ARG configsvr
            ENV configsvr=$configsvr
            ENTRYPOINT su hduser -c 'mongos --port 27017 --bind_ip_all --configdb $configsvr | tee ~/mongologs/db$replicaset/log'
        """,
        "base":"""
            FROM ubuntu:latest
            RUN apt-get update && apt-get upgrade -y
            RUN apt-get -y install openssh-server mongodb
            RUN useradd hduser -d /home/hduser -g sudo -m
            RUN echo hduser:'basmat!Pass9' | chpasswd
            RUN echo "hduser ALL = NOPASSWD: ALL" | tee -a /etc/sudoers
            RUN echo "AllowUsers hduser" | tee -a /etc/ssh/sshd_config
        """
    }

    @docker_queries.route('/docker/getImage/<tag>', methods=['POST'])
    def getImage(tag):
        conf = request.json
        baseUrl = conf.get('base_url','unix://var/run/docker.sock')
        
        #Connect to docker
        c = docker.DockerClient(base_url=baseUrl,version='auto')
        try:
            img = c.images.get(tag)
            if(img is None):
                return gzipencode(json.dumps({'error':'Image not found.'}),'application/json',request.headers.get('Accept-Encoding'))
            info = {}
            try: info['id'] = img.id
            except: None
            try: info['name'] = img.name
            except: None
            try: info['labels'] = img.labels
            except: None
            try: info['tags'] = img.tags
            except: None
            return gzipencode(json.dumps(info),'application/json',request.headers.get('Accept-Encoding'))
        except Exception as ex:
            print(ex)
            c.close()
            return gzipencode(json.dumps({'error':str(ex)}),'application/json',request.headers.get('Accept-Encoding'))
    
    @docker_queries.route('/docker/clearContainers/<username>', methods=['POST'])
    def clearContainers(username):
        conf = request.json
        baseUrl = conf.get('base_url','unix://var/run/docker.sock')
        
        #Connect to docker
        c = docker.DockerClient(base_url=baseUrl,version='auto')
        try:
            resultList = []
            containers = c.containers.list(filters={'label':'user='+username},all=True)
            for container in containers:
                try:
                    id=container.short_id
                    container.remove(force=True)
                    resultList.append({'removed':id})
                except Exception as exex:
                    resultList.append({'error':id,'exception':str(exex)})
            c.close()
            return gzipencode(json.dumps(resultList),'application/json',request.headers.get('Accept-Encoding'))
        except Exception as ex:
            print(ex)
            c.close()
            return gzipencode(json.dumps({'error':ex,'username_provided':username}),'application/json',request.headers.get('Accept-Encoding'))
    
    @docker_queries.route('/docker/listContainers/<username>', methods=['POST'])
    def listContainers(username):
        conf = request.json
        baseUrl = conf.get('base_url','unix://var/run/docker.sock')
        
        #Connect to docker
        c = docker.DockerClient(base_url=baseUrl,version='auto')
        try:
            resultList = []
            containers = c.containers.list(filters={'label':'user='+username},all=True)
            for container in containers:
                info = {}
                try: info['short_id'] = container.short_id
                except: None
                try: info['status'] = container.status
                except: None
                try: info['name'] = container.name
                except: None
                try: info['type'] = container.labels['type']
                except: None
                try: info['port'] = container.labels['port']
                except: None
                try: info['image'] = {'tags':container.image.tags,'labels':container.image.labels}
                except: None
                if('image' in info and 'tags' in info['image'] and info['image']['tags'] != None and len(info['image']['tags']) > 0):
                    resultList.append(info)
            c.close()
            return gzipencode(json.dumps(resultList),'application/json',request.headers.get('Accept-Encoding'))
        except Exception as ex:
            print(ex)
            c.close()
            return gzipencode(json.dumps({'error':ex,'username_provided':username}),'application/json',request.headers.get('Accept-Encoding'))
            
    @docker_queries.route('/docker/removeContainer', methods=['POST'])
    def removeContainer(conf = None):
        if(conf == None):
            conf = request.json
        baseUrl = conf.get('base_url','unix://var/run/docker.sock')
        cID = conf.get('id',None)
        if(cID is not None):
            #Connect to docker
            c = docker.DockerClient(base_url=baseUrl,version='auto')
            try:
                result = {}
                container = c.containers.get(cID)
                try:
                    id=container.short_id
                    container.remove(force=True)
                    result={'removed':id}
                except Exception as exex:
                    result={'error':id,'exception':str(exex)}
                c.close()
                return gzipencode(json.dumps(result),'application/json',request.headers.get('Accept-Encoding'))
            except Exception as ex:
                print(ex)
                c.close()
                return gzipencode(json.dumps({'error':ex,'id_provided':cID}),'application/json',request.headers.get('Accept-Encoding'))
        else:
            return gzipencode(json.dumps({'error':'No container ID provided','id_provided':cID}),'application/json',request.headers.get('Accept-Encoding'))
    
    @docker_queries.route('/docker/stopContainer', methods=['POST'])
    def stopContainer(conf = None):
        if(conf == None):
            conf = request.json
        baseUrl = conf.get('base_url','unix://var/run/docker.sock')
        cID = conf.get('id',None)
        if(cID is not None):
            #Connect to docker
            c = docker.DockerClient(base_url=baseUrl,version='auto')
            try:
                container = c.containers.get(cID)
                container.stop()
                c.close()
                return gzipencode(json.dumps({'success':cID}),'application/json',request.headers.get('Accept-Encoding'))
            except Exception as ex:
                print(ex)
                c.close()
                return gzipencode(json.dumps({'error':cID,'exception':str(ex)}),'application/json',request.headers.get('Accept-Encoding'))
        else:
            return gzipencode(json.dumps({'error':'No container ID provided','id_provided':cID}),'application/json',request.headers.get('Accept-Encoding'))
            
    @docker_queries.route('/docker/runContainer', methods=['POST'])
    def runContainer(conf = None):
        try:
            if(conf == None):
                conf = request.json
            baseUrl = conf.get('base_url','unix://var/run/docker.sock')
            
            #Connect to docker
            c = docker.DockerClient(base_url=baseUrl,version='auto')
            
            cID = conf.get('id',None)
            
            if(cID is not None):
                container = c.containers.get(cID)
                container.start()
                c.close()
                return gzipencode(json.dumps(cID),'application/json',request.headers.get('Accept-Encoding'))
            
            username = conf.get('username',None)
            if(username is None):
                return gzipencode(json.dumps({'error':'Did not provide username.'}),'application/json',request.headers.get('Accept-Encoding'))
                
            serverType = conf.get('type','shard')
            hostPort = int(conf.get('hostport',default_host_ports[serverType]))
            port = conf.get('port',{default_ports[serverType]:hostPort})
            hostIP = conf.get('host','localhost')
            replicaSet = conf.get('rs','0')
            
            container = c.containers.run('rs'+replicaSet.lower()+'_'+serverType+"_server", detach=True, ports=port, labels={'host':str(hostIP),'user':str(username),'type':str(serverType),'port':str(hostPort)})
            cID = container.short_id
            c.close()
            return gzipencode(json.dumps({'started':cID}),'application/json',request.headers.get('Accept-Encoding'))
        except Exception as ex:
            track = traceback.format_exc()
            print(track)
            return gzipencode(json.dumps({'error':str(ex)}),'application/json',request.headers.get('Accept-Encoding'))
            
    @docker_queries.route('/docker/listImages/<username>', methods=['POST'])
    def listImages(username):
        conf = request.json
        baseUrl = conf.get('base_url','unix://var/run/docker.sock')
        
        #Connect to docker
        c = docker.DockerClient(base_url=baseUrl,version='auto')
        try:
            resultList = []
            images = c.images.list(all=True)
            for image in images:
                if 'ubuntu_base:latest' in image.tags:
                    info = {}
                    try: info['short_id'] = image.short_id
                    except: None
                    try: info['tags'] = image.tags
                    except: None
                    try: info['labels'] = image.labels
                    except: None
                    resultList.append(info)
                    print(info)
            images = c.images.list(filters={'label':'user='+username},all=True)
            for image in images:
                info = {}
                try: info['short_id'] = image.short_id
                except: None
                try: info['tags'] = image.tags
                except: None
                try: info['labels'] = image.labels
                except: None
                resultList.append(info)
                print(info)
            c.close()
            return gzipencode(json.dumps(resultList),'application/json',request.headers.get('Accept-Encoding'))
        except Exception as ex:
            print(ex)
            c.close()
            return gzipencode(json.dumps({'error':ex,'username_provided':username}),'application/json',request.headers.get('Accept-Encoding'))
        
    @docker_queries.route('/docker/buildImage', methods=['POST'])
    def buildImage(conf = None):
        try:
            if(conf == None):
                conf = request.json
            if(conf == None):
                conf = {}
            
            baseUrl = conf.get('base_url','unix://var/run/docker.sock')
            
            username = conf.get('username',None)
            if(username is None):
                return gzipencode(json.dumps({'error':'Did not provide username.'}),'application/json',request.headers.get('Accept-Encoding'))
            
            serverType = conf.get('type','shard')
            replicaSet = conf.get('rs','0')
            configHost = conf.get('config_host','rsC/localhost:27018')
            dockerfile = dockerfiles.get(serverType,None)
            if(dockerfile is None):
                return gzipencode(json.dumps({'error':'Server Type not supported {'+serverType+'}'}),'application/json',request.headers.get('Accept-Encoding'))
            
            #Connect to docker
            c = docker.APIClient(base_url=baseUrl,version='auto')
            if(serverType == "base"):
                buildLogs = c.build(fileobj=io.BytesIO(dockerfile.encode('utf-8')),labels={'type':serverType},tag='ubuntu_base',decode=True)
            else:
                buildLogs = c.build(fileobj=io.BytesIO(dockerfile.encode('utf-8')),labels={'user':username,'type':serverType,'rs':replicaSet,'configHost':configHost},tag='rs'+replicaSet.lower()+'_'+serverType+'_server',buildargs={'configsvr':configHost,'replicaset':replicaSet},decode=True)
            
            def generate():
                streamEnded = False
                for line in buildLogs:
                    if not streamEnded:
                        try:
                            print(line['stream'])
                            if 'Successfully tagged' in line['stream']:
                                streamEnded = True
                            yield line['stream']
                        except: 
                            c.close()
                    else:
                        break
            # return Response(generate(), mimetype='text/plain') 
            return gzipencode(generate(),'application/json',request.headers.get('Accept-Encoding'))
        except Exception as ex:
            return gzipencode(json.dumps({'error':str(ex)}),'application/json',request.headers.get('Accept-Encoding'))
        
    @docker_queries.route('/docker/info', methods=['POST'])
    def info(conf = None):
        try:
            if(conf == None):
                conf = request.json
            if(conf == None):
                    conf = {}
            
            baseUrl = conf.get('base_url','unix://var/run/docker.sock')
            
            #Connect to docker
            c = docker.DockerClient(base_url=baseUrl,version='auto')
            dinfo = c.info()
            c.close()
            return gzipencode(json.dumps(dinfo),'application/json',request.headers.get('Accept-Encoding'))
        except Exception as ex:
            return gzipencode(json.dumps({'error':str(ex)}),'application/json',request.headers.get('Accept-Encoding'))
    
    return docker_queries