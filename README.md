# DITAS_Marketplace_Repository_Scaling
This repository contains all the API methods and UI of the Marketplace Repository Scaling

## Introduction

The Marketplace Repository Scaling is essentially a database management system for the DITAS Marketplace. It is used to improve the response times and general performance of the Resolution Engine by monitoring the utilization and performance of it's repositories. It is studying the choke points and tries to amend them by taking advantage of the container technology and the opportunity that MongoDB provides to cluster on the fly (from 3.6+ version). It can instantiate new MongoDB clusters and add new servers to the cluster or remove an unused server from the cluster during runtime, providing assistance to overloaded servers or removing underloaded ones, freeing unused resources. Three requirements are tackled using this component; It ensures business continuity and disaster recovery by using the scaling mechanisms of MongoDB, adding redundancy and availability of the services, thus addressing the requirement T3.6. At the same time this scalability aids the Resolution Engine scalability by matching any scaling process with the scaling process in the appropriate underlying repository, better addressing the requirement T3.10. Finally, by employing Docker, we can use dynamic architectures for the repositories, making use of machines of various capabilities, types, and topologies addressing the requirement B3.6. More information about the requirements can be found in [deliverable D1.2](https://www.ditas-project.eu/wp-content/uploads/2019/01/DITAS-D1.2-Final-Archictecture-and-Validation-1.0-3.pdf).

## License
This file is part of DITAS Marketplace Repository Scaling.

DITAS Marketplace Repository Scaling is free software: you can redistribute it 
and/or modify it under the terms of the GNU General Public License as 
published by the Free Software Foundation, either version 3 of the License, 
or (at your option) any later version.

DITAS Marketplace Repository Scaling is distributed in the hope that it will be 
useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with DITAS Marketplace Repository Scaling.  
If not, see <https://www.gnu.org/licenses/>.

DITAS Marketplace Repository Scaling is being developed for the
DITAS Project: https://www.ditas-project.eu/

## Functionalities 
* `POST` `/manager/runCluster`
  * **description**: This method creates and runs a new cluster by using the provided JSON configuration.
  * **input**: Cluster configuration JSON file
  * **output**: The access point of the new cluster

* `POST` `/manager/destroyCluster`  
  * **description**: This method destroys a cluster and deletes the containers used in it.
  * **input**: Cluster access point and username in JSON file format
  * **output**: success or error message

* `POST` `/docker/buildImage`  
  * **description**: This method builds a docker image to be used in cluster creations.
  * **input**: Configuration of the image in JSON file
  * **output**: The id of the new image
  
* `POST` `/manager/addServer`  
  * **description**: This method adds a new server to the cluster, scaling it out.
  * **input**: Configuration of the container to add to the cluster in JSON file
  * **output**: success or error message
  
* `POST` `/manager/removeServer`  
  * **description**: This method removes a server from the cluster, scaling it in.
  * **input**: The container ID to be removed in a JSON file
  * **output**: success or error message
  
## Language
* Python
* Javascript

## Requirements
* Python 3.2+

## Installation
Clone repository

## Execution
* Install pipenv using the Pipfile in the python folder
* Execute the following in the python folder: 
  * pipenv run gunicorn -w 4 -b 0.0.0.0:5000 -t 5000 "mongoManagerService:create_app()"
* Open the index.html page in web folder with a browser
