/*
 * This file is part of DITAS Marketplace Repository Scaling.
 * 
 * DITAS Marketplace Repository Scaling is free software: you can redistribute it 
 * and/or modify it under the terms of the GNU General Public License as 
 * published by the Free Software Foundation, either version 3 of the License, 
 * or (at your option) any later version.
 * 
 * DITAS Marketplace Repository Scaling is distributed in the hope that it will be 
 * useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License
 * along with DITAS Marketplace Repository Scaling.  
 * If not, see <https://www.gnu.org/licenses/>.
 * 
 * DITAS Marketplace Repository Scaling is being developed for the
 * DITAS Project: https://www.ditas-project.eu/
 */
var server = "http://localhost:8000";
var dockerHost = "";
var username = "";
function login(){
	username = $('#usernameInput').val();
	dockerHost = $('#dockerhostInput').val();
	$('#loginTab').addClass('d-none');
	createImagesTable();
	createContainersTable();
	createClustersTable();
	$('#imagesTab').removeClass('d-none');
	$('#containersTab').removeClass('d-none');
	$('#clustersTab').removeClass('d-none');
	$( "#mainContent" ).tabs({active: 1});
	return true;
}

function createContainersTable(){
	$('#containersArray').removeClass('d-none');
	$('#containersArray').addClass('d-none');
	$('#containersLoading').removeClass('d-none');
	$.ajax({
		'type':'POST',
		'url':server+'/docker/listContainers/'+username,
		'async':true,
		'contentType': 'application/json; charset=utf-8',
        'dataType': 'json',
		'data':JSON.stringify({"base_url":dockerHost}),
		'success':function(dat){
			let html = '<tr><th>ID</th><th>Port</th><th>Status</th><th>Type</th><th>ReplicaSet</th><th>Configuration Server</th><th class="actionsDiv">Actions</th></tr>';
			for(let row=0;row<dat.length;row++){
				let containerRow = dat[row];
				html+= '<tr><td>'+containerRow['short_id']+'</td>';
				if(containerRow['port']){html+= '<td>'+containerRow['port']+'</td>';}
				else{html+= '<td></td>';}
				if(containerRow['status']){html+= '<td>'+containerRow['status']+'</td>';}
				else{html+= '<td></td>';}
				if(containerRow['type']){html+= '<td>'+containerRow['type']+'</td>';}
				else{html+= '<td></td>';}
				if(containerRow['image']['labels']['rs']){html+= '<td>'+containerRow['image']['labels']['rs']+'</td>';}
				else{html+= '<td></td>';}
				if(containerRow['image']['labels']['configHost']){html+= '<td>'+containerRow['image']['labels']['configHost']+'</td>';}
				else{html+= '<td></td>';}
				html+= '<td class="actionsDiv">';
				html+='<span class="containerPowerButton actionButton powerButton" title="Stop/Start"></span>';
				html+='<span class="containerDestroyButton actionButton deleteButton" title="Remove"></span>';
				html+= '</td></tr>';
			}
			$('#containersArray').html(html);
			$('#containersArray').removeClass('d-none');
			$('#containersLoading').addClass('d-none');
		},
		'error':function(errMsg){
			console.log(errMsg);
		}
	});
}

function createImagesTable(){
	$('#imagesArray').removeClass('d-none');
	$('#imagesArray').addClass('d-none');
	$('#imagesLoading').removeClass('d-none');
	$.ajax({
		'type':'POST',
		'url':server+'/docker/listImages/'+username,
		'async':true,
		'contentType': 'application/json; charset=utf-8',
        'dataType': 'json',
		'data':JSON.stringify({"base_url":dockerHost}),
		'success':function(dat){
			let html = '<tr><th>ID</th><th>Type</th><th>ReplicaSet</th><th>Configuration Server</th><th class="actionsDiv">Actions</th></tr>';
			for(let row=0;row<dat.length;row++){
				let imageRow = dat[row];
				html+= '<tr><td>'+imageRow['short_id']+'</td>';
				if(imageRow['labels']['type']){html+= '<td>'+imageRow['labels']['type']+'</td>';}
				else{html+= '<td></td>';}
				if(imageRow['labels']['rs']){html+= '<td>'+imageRow['labels']['rs']+'</td>';}
				else{html+= '<td></td>';}
				if(imageRow['labels']['configHost']){html+= '<td>'+imageRow['labels']['configHost']+'</td>';}
				else{html+= '<td></td>';}
				html+= '<td class="actionsDiv">';
				html+='<span class="imageDestroyButton actionButton deleteButton" title="Remove"></span>';
				html+= '</td></tr>';
			}
			$('#imagesArray').html(html);
			$('#imagesArray').removeClass('d-none');
			$('#imagesLoading').addClass('d-none');
		},
		'error':function(errMsg){
			console.log(errMsg);
		}
	});
}

function createClustersTable(){
	$('#clustersArray').removeClass('d-none');
	$('#clustersArray').addClass('d-none');
	$('#clustersLoading').removeClass('d-none');
	$.ajax({
		'type':'GET',
		'url':server+'/manager/getClusterMaps/'+username,
		'async':true,
		'contentType': 'application/json; charset=utf-8',
		'success':function(dat){
			let html = '';
			for(let row=0;row<dat.length;row++){
				let clusterRow = dat[row];
				if(clusterRow['access_point']){
					html+='<tr><td><table class="clusterRow"><tr class="clusterAP"><th>'+clusterRow['access_point'];
					html+='</th><th class="actionsDiv">';
					html+='<span class="clusterPowerButton actionButton powerButton" title="Stop/Start"></span>';
					html+='<span class="clusterDestroyButton actionButton deleteButton" title="Remove"></span>';
					html+='<span class="clusterScaleOutButton actionButton scaleUpButton" title="Scale Out"></span>';
					html+='<span class="clusterScaleInButton actionButton scaleDownButton" title="Scale In"></span>';
					html+='</th></tr>';
					
					for (let key in clusterRow){
						if(clusterRow.hasOwnProperty(key)){
							if(key == 'config'){
								html+='<tr clas="clusterInfo"><td>Config</td>';
								html+='<td>'+clusterRow[key]+'</td>';
								html+='</tr>';
							}else if(key != 'access_point'){
								html+='<tr clas="clusterInfo"><td>Shard</td>';
								html+='<td>'+clusterRow[key]+'</td>';
								html+='</tr>';
							}
						}
					}
				}
				html+='</table></td></tr>';
			}
			$('#clustersArray').html(html);
			$('#clustersArray').removeClass('d-none');
			$('#clustersLoading').addClass('d-none');
		},
		'error':function(errMsg){
			console.log(errMsg);
		}
	});
	return true;
}

function createImage(){
	let data={
		"base_url":dockerHost,
		"username":username,
		"type": $('.imageDataField[data-field="type"]').val(),
		"rs": $('.imageDataField[data-field="rs"]').val(),
		"config_host": $('.imageDataField[data-field="config_host"]').val()
	};
	getStreamData(server+'/docker/buildImage',data,'#imageStreamConsole',createImagesTable);
	return true;
}

function runContainer(){ //{"error": "HTTPConnectionPool(host='localhost', port=2375): Read timed out. (read timeout=60)"}
	let data={
		"base_url":dockerHost,
		"username":username,
		"type": $('.containerDataField[data-field="type"]').val(),
		"hostport": $('.containerDataField[data-field="port"]').val(),
		"host": $('.containerDataField[data-field="host"]').val(),
		"rs": $('.containerDataField[data-field="rs"]').val()
	};
	getStreamData(server+'/docker/runContainer',data,'#containerStreamConsole',createContainersTable);
	return true;
}

function createCluster(){
	try{
		let data= JSON.parse($('#createClusterTextarea').val());
		if(!data['base_url']){
			data['base_url'] = dockerHost;
		}
		if(!data['username']){
			data['username'] = username;
		}
		getStreamData(server+'/manager/runCluster',data,'#clusterStreamConsole',createClustersTable);
	}catch(exc){console.log(exc);}
	return true;
}

//End stream when complete message is detected

function getStreamData(url,data,consoleElem,doneHandler) {
    var xhr = new XMLHttpRequest();
    xhr.open('POST', url, true);
	xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
    xhr.send([JSON.stringify(data)]);
    var timer;
    timer = window.setInterval(function() {
        if (xhr.readyState == XMLHttpRequest.DONE) {
            window.clearTimeout(timer);
            console.log('done');
			$(consoleElem).html($('#imageStreamConsole').html()+'<br/>done');
			$(consoleElem).scrollTop($('#imageStreamConsole')[0].scrollHeight);
			if(doneHandler){
				doneHandler();
			}
        }
		let res = xhr.responseText;
		$(consoleElem).html(res.split("\n").join('<br/>'));
		$(consoleElem).scrollTop($(consoleElem)[0].scrollHeight);
        console.log(res);
    }, 500);
}

$(document).ready(function(){
	$( "#mainContent" ).tabs({active: 0});
});